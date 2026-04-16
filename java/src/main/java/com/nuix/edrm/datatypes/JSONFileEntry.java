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
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();

    private final Path jsonPath;
    private final Map<String, EntryField.Type> fieldTypeOverrides = new LinkedHashMap<>();

    // Generator classes (null = use default)
    private Class<? extends JSONValueEntry>  valueClass  = null;
    private Class<? extends JSONArrayEntry>  arrayClass  = null;
    private Class<? extends JSONObjectEntry> objectClass = null;

    // --- Constructors ---

    public JSONFileEntry(String jsonFilePath) {
        this(jsonFilePath, "application/json", null);
    }

    public JSONFileEntry(String jsonFilePath, String mimeType, String parentId) {
        super(jsonFilePath, mimeType, parentId);
        this.jsonPath = Path.of(jsonFilePath).toAbsolutePath();
    }

    public JSONFileEntry(String jsonFilePath, String mimeType, String parentId,
                         Class<? extends JSONValueEntry>  valueClass,
                         Class<? extends JSONArrayEntry>  arrayClass,
                         Class<? extends JSONObjectEntry> objectClass) {
        this(jsonFilePath, mimeType, parentId);
        this.valueClass  = valueClass;
        this.arrayClass  = arrayClass;
        this.objectClass = objectClass;
    }

    // --- Field-type override API ---

    /**
     * Register a JSONPath → DataType override. Applied at traversal time when the path of a
     * scalar node matches the pattern.
     *
     * <p>Supported pattern forms:
     * <ul>
     *   <li>{@code $..key} — recursive descent; matches any field named {@code key}</li>
     *   <li>{@code $.key} — root-level key</li>
     *   <li>{@code $.parent.key} — exact nested path</li>
     *   <li>{@code $.arr[*].key} — {@code key} inside any element of array {@code arr}</li>
     * </ul>
     *
     * @throws IllegalArgumentException if {@code jsonPathPattern} is malformed (e.g. ends
     *         with a dot, contains consecutive dots, or has an empty segment)
     */
    public void addFieldTypeOverride(String jsonPathPattern, EntryField.Type type) {
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

            // Use factory so valueClass override is respected
            JSONValueEntry entry = JsonEntryFactory.createValue(
                    nodeName, nodeName, value, "application/x-json-value", parentId, valueClass);

            // Apply field-type override if present
            if (overrideType != null) {
                entry.putField(FieldFactory.generateField(nodeName, overrideType, value));
            }

            entry.addToBuilder(builder);

        } else if (node.isArray()) {
            List<Object> array = jacksonArrayToList(node, pathStack);
            JSONArrayEntry entry = JsonEntryFactory.createArray(
                    nodeName, array, "application/x-json-array", parentId, arrayClass);
            entry.addToBuilder(builder);

        } else if (node.isObject()) {
            Map<String, Object> object = jacksonObjectToMap(node, pathStack);
            JSONObjectEntry entry = JsonEntryFactory.createObject(
                    nodeName, object, "application/x-json-object", parentId, objectClass);
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

        // Recursive descent: $..key matches any path whose last segment == key
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
     *
     * <p>This method validates that no segment is empty — an empty segment indicates a
     * malformed pattern such as a trailing dot ({@code $.foo.}) or consecutive dots
     * ({@code $.foo..bar}). Such patterns are rejected with a clear error rather than
     * silently producing incorrect matches.
     *
     * @throws IllegalArgumentException if the pattern produces an empty segment (malformed)
     */
    private static List<String> parseJsonPathSegments(String pattern) {
        String rest = pattern.substring(2); // strip '$.'
        rest = rest.replace("[*]", ".*");
        String[] parts = rest.split("\\.", -1); // -1 preserves trailing empty strings
        for (String part : parts) {
            if (part.isEmpty()) {
                throw new IllegalArgumentException(
                        "Malformed JSONPath pattern: empty segment in \"" + pattern + "\". " +
                        "Check for trailing dots, leading dots after '$', or consecutive dots.");
            }
        }
        return Arrays.asList(parts);
    }

    /**
     * Validate a JSONPath pattern supplied to {@link #addFieldTypeOverride}.
     * Throws {@link IllegalArgumentException} for patterns that would produce
     * silent incorrect matches (e.g. trailing dots, consecutive dots, missing prefix).
     */
    private static void validateJsonPathPattern(String pattern) {
        if (pattern == null || pattern.isEmpty()) {
            throw new IllegalArgumentException("JSONPath pattern must not be null or empty.");
        }
        if (!pattern.startsWith("$")) {
            throw new IllegalArgumentException(
                    "JSONPath pattern must start with '$': \"" + pattern + "\"");
        }
        if (pattern.startsWith("$..")) {
            // Recursive-descent pattern: $..key — key must be non-empty
            String key = pattern.substring(3);
            if (key.isEmpty()) {
                throw new IllegalArgumentException(
                        "Malformed JSONPath pattern: '$..'' must be followed by a non-empty key.");
            }
            return;
        }
        if (!pattern.startsWith("$.")) {
            throw new IllegalArgumentException(
                    "JSONPath pattern must start with '$.' or '$..': \"" + pattern + "\"");
        }
        // Delegate to segment parser which validates empty segments
        parseJsonPathSegments(pattern);
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
