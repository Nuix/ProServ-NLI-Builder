package com.nuix.edrm.datatypes;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.FieldFactory;
import com.nuix.edrm.FileEntry;
import com.nuix.nli.CompoundEntry;

import java.io.IOException;
import java.nio.file.Path;
import java.util.*;

/**
 * Compound entry for JSON files. Uses Jackson to parse the JSON tree and dispatches to:
 * <ul>
 *   <li>{@link JSONValueEntry} for scalar root values</li>
 *   <li>{@link JSONArrayEntry} for array root values</li>
 *   <li>{@link JSONObjectEntry} for object root values</li>
 * </ul>
 * Nested arrays and objects are added as child entries with correct parent-child relationships.
 *
 * <h3>JSONPath field-type overrides</h3>
 * Call {@link #addFieldTypeOverride(String, EntryField.Type)} to force a particular DataType
 * on scalar fields matched by a JSONPath pattern. Supported pattern forms:
 * <ul>
 *   <li>{@code $..key} — recursive descent; matches any field named {@code key}</li>
 *   <li>{@code $.key} — root-level key</li>
 *   <li>{@code $.parent.key} — exact nested path</li>
 *   <li>{@code $.arr[*].key} — {@code key} inside any element of array {@code arr}</li>
 * </ul>
 */
public class JSONFileEntry extends FileEntry implements CompoundEntry {
    // ObjectMapper is thread-safe once fully configured and thereafter immutable in use.
    // Sharing a single static instance avoids per-instance allocation overhead.
    // Do NOT call configuration methods (e.g. configure(), registerModule()) on this field
    // after class initialisation — those calls are not thread-safe once the mapper is in use.
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private final Path jsonPath;
    private final Map<String, EntryField.Type> fieldTypeOverrides = new LinkedHashMap<>();

    // Generator factories (null = use default)
    private JsonEntryFactory.ValueGenerator  valueGenerator  = null;
    private JsonEntryFactory.ArrayGenerator  arrayGenerator  = null;
    private JsonEntryFactory.ObjectGenerator objectGenerator = null;

    // --- Constructors ---

    public JSONFileEntry(String jsonFilePath) {
        this(jsonFilePath, "application/json", null);
    }

    public JSONFileEntry(String jsonFilePath, String mimeType, String parentId) {
        super(jsonFilePath, mimeType, parentId);
        this.jsonPath = Path.of(jsonFilePath).toAbsolutePath();
    }

    public JSONFileEntry(String jsonFilePath, String mimeType, String parentId,
                         JsonEntryFactory.ValueGenerator  valueGenerator,
                         JsonEntryFactory.ArrayGenerator  arrayGenerator,
                         JsonEntryFactory.ObjectGenerator objectGenerator) {
        this(jsonFilePath, mimeType, parentId);
        this.valueGenerator  = valueGenerator;
        this.arrayGenerator  = arrayGenerator;
        this.objectGenerator = objectGenerator;
    }

    // --- Field-type override API ---

    /**
     * Validate a JSONPath pattern before registering it as a field-type override.
     *
     * <p>Supported forms:
     * <ul>
     *   <li>{@code $..key} — recursive descent to a single key name (no dots allowed in key)</li>
     *   <li>{@code $.key} — root-level key</li>
     *   <li>{@code $.parent.key} — exact nested path</li>
     *   <li>{@code $.arr[*].key} — key inside any array element</li>
     * </ul>
     *
     * <p>Patterns of the form {@code $..foo.bar} are rejected. The key extracted after {@code $..}
     * would be {@code "foo.bar"}, which can never match a real JSON field name, making the override
     * a silent no-op.  Callers should use {@code $.foo.bar} for exact paths or {@code $..bar} for
     * single-level recursive descent.
     *
     * @param pattern the JSONPath pattern to validate
     * @throws IllegalArgumentException if the pattern is null, does not start with {@code $}, or
     *                                  uses {@code $..} with a dotted (nested) key
     */
    static void validateJsonPathPattern(String pattern) {
        if (pattern == null || !pattern.startsWith("$")) {
            throw new IllegalArgumentException(
                    "Malformed JSONPath pattern: must start with '$': \"" + pattern + "\"");
        }
        if (pattern.startsWith("$..")) {
            String key = pattern.substring(3);
            if (key.isEmpty()) {
                throw new IllegalArgumentException(
                        "Malformed JSONPath pattern: '$..key' requires a non-empty key name: \"" + pattern + "\"");
            }
            if (key.contains(".")) {
                throw new IllegalArgumentException(
                        "Malformed JSONPath pattern: '$..key' does not support nested paths. "
                        + "Use '$.parent.key' for exact paths or '$..key' for a single-level key: \""
                        + pattern + "\"");
            }
        }
    }

    /**
     * Register a JSONPath → DataType override. Applied at traversal time when the path of a
     * scalar node matches the pattern.
     *
     * @throws IllegalArgumentException if the pattern is malformed (see {@link #validateJsonPathPattern}),
     *                                  or if {@code type} is null
     */
    public void addFieldTypeOverride(String jsonPathPattern, EntryField.Type type) {
        if (type == null) {
            throw new IllegalArgumentException("Field type must not be null.");
        }
        validateJsonPathPattern(jsonPathPattern);
        fieldTypeOverrides.put(jsonPathPattern, type);
    }

    // --- CompoundEntry ---

    @Override
    public String addToBuilder(EDRMBuilder builder) {
        builder.addEntry(this);
        String myId = getField(getIdentifierField()).getValue().toString();

        JsonNode root;
        try {
            root = OBJECT_MAPPER.readTree(jsonPath.toFile());
        } catch (IOException e) {
            throw new RuntimeException("Failed to parse JSON file: " + jsonPath, e);
        }

        if (root == null || root.isNull() || root.isMissingNode()) {
            return myId;
        }

        // Mirror Python: root child is always named "JSON Value", "JSON Array", or "JSON Object"
        String rootName;
        if (root.isValueNode()) {
            rootName = "JSON Value";
        } else if (root.isArray()) {
            rootName = "JSON Array";
        } else {
            rootName = "JSON Object";
        }
        List<String> pathStack = new ArrayList<>();

        addNodeToBuilder(builder, root, rootName, myId, pathStack);

        return myId;
    }

    // --- Recursive traversal ---

    private void addNodeToBuilder(
            EDRMBuilder builder,
            JsonNode node,
            String nodeName,
            String parentId,
            List<String> pathStack) {

        if (node.isValueNode()) {
            // Scalar — determine Java type from JsonNode
            Object value = extractScalarValue(node);

            // Check for JSONPath type override
            EntryField.Type overrideType = resolveTypeOverride(pathStack);

            // Use factory so valueGenerator override is respected
            JSONValueEntry entry = JsonEntryFactory.createValue(
                    nodeName, nodeName, value, "application/x-json-value", parentId, valueGenerator);

            // Apply field-type override if present
            if (overrideType != null) {
                entry.putField(FieldFactory.generateField(nodeName, overrideType, value));
            }

            entry.addToBuilder(builder);

        } else if (node.isArray()) {
            List<Object> array = jacksonArrayToList(node, pathStack);
            JSONArrayEntry entry = JsonEntryFactory.createArray(
                    nodeName, array, "application/x-json-array", parentId, arrayGenerator);
            entry.addToBuilder(builder);

        } else if (node.isObject()) {
            Map<String, Object> object = jacksonObjectToMap(node, pathStack);
            JSONObjectEntry entry = JsonEntryFactory.createObject(
                    nodeName, object, "application/x-json-object", parentId, objectGenerator);
            entry.addToBuilder(builder);
        }
    }

    /**
     * Convert a Jackson ArrayNode into a List&lt;Object&gt; where nested arrays remain as List
     * and nested objects remain as Map, allowing JSONArrayEntry to partition them correctly.
     * Scalar values are coerced to the Java type demanded by any matching fieldTypeOverride so
     * that MappingEntry.fillInitialFields assigns the correct DataType at construction time.
     */
    private List<Object> jacksonArrayToList(JsonNode arrayNode, List<String> pathStack) {
        List<Object> list = new ArrayList<>();
        int i = 0;
        for (JsonNode element : arrayNode) {
            pathStack.add(String.valueOf(i));
            if (element.isValueNode()) {
                list.add(coerceScalar(element, pathStack));
            } else if (element.isArray()) {
                list.add(jacksonArrayToList(element, pathStack));
            } else if (element.isObject()) {
                list.add(jacksonObjectToMap(element, pathStack));
            }
            pathStack.remove(pathStack.size() - 1);
            i++;
        }
        return list;
    }

    /**
     * Convert a Jackson ObjectNode into a Map&lt;String, Object&gt; preserving nested structure.
     * Scalar values are coerced to the Java type demanded by any matching fieldTypeOverride so
     * that MappingEntry.fillInitialFields assigns the correct DataType at construction time.
     */
    private Map<String, Object> jacksonObjectToMap(JsonNode objectNode, List<String> pathStack) {
        Map<String, Object> map = new LinkedHashMap<>();
        objectNode.fields().forEachRemaining(e -> {
            String key = e.getKey();
            JsonNode value = e.getValue();
            pathStack.add(key);
            if (value.isValueNode()) {
                map.put(key, coerceScalar(value, pathStack));
            } else if (value.isArray()) {
                map.put(key, jacksonArrayToList(value, pathStack));
            } else if (value.isObject()) {
                map.put(key, jacksonObjectToMap(value, pathStack));
            }
            pathStack.remove(pathStack.size() - 1);
        });
        return map;
    }

    /**
     * Extract a Java scalar from a Jackson value node, then coerce its type to match any
     * fieldTypeOverride registered for the current path.  Coercion rules:
     * <ul>
     *   <li>DateTime override: string value → OffsetDateTime (if parseable)</li>
     *   <li>LongInteger override: numeric/string → Long</li>
     *   <li>Decimal override: numeric/string → Double</li>
     *   <li>Boolean override: string "true"/"false" → Boolean</li>
     *   <li>Text/LongText override: any → String</li>
     *   <li>No match or unparseable: raw Java value unchanged</li>
     * </ul>
     */
    private Object coerceScalar(JsonNode node, List<String> pathStack) {
        Object raw = extractScalarValue(node);
        EntryField.Type override = resolveTypeOverride(pathStack);
        if (override == null) return raw;
        try {
            switch (override) {
                case DateTime: {
                    if (raw instanceof java.time.OffsetDateTime) return raw;
                    String s = String.valueOf(raw);
                    return java.time.OffsetDateTime.parse(s);
                }
                case LongInteger: {
                    if (raw instanceof Long) return raw;
                    if (raw instanceof Number) return ((Number) raw).longValue();
                    return Long.parseLong(String.valueOf(raw));
                }
                case Decimal: {
                    if (raw instanceof Double) return raw;
                    if (raw instanceof Number) return ((Number) raw).doubleValue();
                    return Double.parseDouble(String.valueOf(raw));
                }
                case Boolean: {
                    if (raw instanceof Boolean) return raw;
                    return java.lang.Boolean.parseBoolean(String.valueOf(raw));
                }
                case Text:
                case LongText:
                    return raw == null ? "" : String.valueOf(raw);
                default:
                    return raw;
            }
        } catch (Exception ignored) {
            // Coercion failed — leave as raw Java value; field type will be inferred naturally.
            return raw;
        }
    }

    /** Extract a Java scalar from a Jackson value node. */
    private static Object extractScalarValue(JsonNode node) {
        if (node.isBoolean())    return node.booleanValue();
        if (node.isLong())       return node.longValue();
        if (node.isInt())        return (long) node.intValue();
        if (node.isDouble())     return node.doubleValue();
        if (node.isFloat())      return (double) node.floatValue();
        if (node.isBigInteger()) {
            try {
                return node.bigIntegerValue().longValueExact();
            } catch (ArithmeticException e) {
                // Value exceeds Long.MAX_VALUE — fall back to text to avoid data loss.
                return String.valueOf(node.bigIntegerValue());
            }
        }
        if (node.isBigDecimal()) return node.decimalValue().doubleValue();
        if (node.isNull())       return null;
        return node.textValue();
    }

    // --- JSONPath override matching ---

    /**
     * Returns the override type for the current path stack, or null if no override applies.
     * When multiple patterns match, the most specific one wins (most literal segments).
     */
    private EntryField.Type resolveTypeOverride(List<String> pathStack) {
        EntryField.Type best = null;
        int bestScore = Integer.MIN_VALUE;

        for (Map.Entry<String, EntryField.Type> entry : fieldTypeOverrides.entrySet()) {
            String pattern = entry.getKey();
            if (matchesPath(pattern, pathStack)) {
                int score = patternSpecificity(pattern);
                if (score > bestScore) {
                    bestScore = score;
                    best = entry.getValue();
                }
            }
        }
        return best;
    }

    /**
     * Returns true if the JSONPath pattern matches the given path stack.
     * Supported patterns: {@code $..key}, {@code $.key}, {@code $.a.b}, {@code $.a[*].b}
     */
    static boolean matchesPath(String pattern, List<String> path) {
        if (pattern == null || !pattern.startsWith("$")) return false;

        // Recursive descent: $..key intentionally matches ANY path whose last segment equals key,
        // regardless of depth. This means "$..name" matches "$.name", "$.person.name",
        // "$.arr[0].name", etc. — it does NOT require a full recursive walk of the tree;
        // only the final path segment is compared. This is correct behaviour: the semantics
        // of $.. in this codebase are "find this key anywhere in the document", which is
        // fully captured by checking the last segment. Do NOT change this to a full recursive
        // traversal — that would alter the matching semantics.
        if (pattern.startsWith("$..")) {
            String key = pattern.substring(3);
            return !path.isEmpty() && path.get(path.size() - 1).equals(key);
        }

        if (!pattern.startsWith("$.")) return false;

        List<String> segments = parseJsonPathSegments(pattern);
        if (segments.size() != path.size()) return false;

        for (int i = 0; i < segments.size(); i++) {
            String seg = segments.get(i);
            if (!"*".equals(seg) && !seg.equals(path.get(i))) return false;
        }
        return true;
    }

    /**
     * Parse the non-recursive segments of a JSONPath pattern (after {@code $.}).
     * Normalizes {@code [*]} array wildcards to {@code *}.
     */
    private static List<String> parseJsonPathSegments(String pattern) {
        String rest = pattern.substring(2); // strip '$.'
        rest = rest.replace("[*]", ".*");
        return Arrays.asList(rest.split("\\."));
    }

    /**
     * Specificity score: higher = more specific. Recursive descent = 0; direct paths score
     * by the count of literal (non-wildcard) segments.
     */
    private static int patternSpecificity(String pattern) {
        if (pattern.startsWith("$..")) return 0;
        if (!pattern.startsWith("$.")) return -1;
        List<String> segs = parseJsonPathSegments(pattern);
        return (int) segs.stream().filter(s -> !"*".equals(s)).count();
    }
}
