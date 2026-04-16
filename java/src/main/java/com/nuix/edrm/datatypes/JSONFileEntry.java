package com.nuix.edrm.datatypes;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.FileEntry;
import com.nuix.edrm.MappingEntry;
import com.nuix.nli.CompoundEntry;
import org.json.JSONArray;
import org.json.JSONObject;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Represents a JSON file as a compound EDRM entry.
 *
 * <p>When added to an {@link EDRMBuilder} via {@link #addToBuilder}, the file itself
 * becomes the parent entry and its contents are parsed into typed child entries:
 * <ul>
 *   <li>A JSON <em>object</em> at the root produces a single {@link JSONObjectEntry}
 *       child whose fields mirror the object's key-value pairs with proper
 *       {@link EntryField.Type} mapping.</li>
 *   <li>A JSON <em>array</em> at the root produces one {@link JSONValueEntry}
 *       child per array element, each carrying its index and string-serialised value.</li>
 *   <li>A JSON <em>scalar</em> (string, number, boolean) at the root produces a
 *       single {@link JSONValueEntry} child at index 0.</li>
 * </ul>
 */
public class JSONFileEntry extends FileEntry implements CompoundEntry {
    private final Path jsonPath;

    public JSONFileEntry(String jsonFilePath) { this(jsonFilePath, "application/json", null); }

    public JSONFileEntry(String jsonFilePath, String mimeType, String parentId) {
        super(jsonFilePath, mimeType, parentId);
        this.jsonPath = Path.of(jsonFilePath).toAbsolutePath();
    }

    @Override
    public String addToBuilder(EDRMBuilder builder) {
        String fileId = builder.addEntry(this);

        try {
            String content = Files.readString(jsonPath).trim();
            parseAndAddChildren(builder, content, fileId);
        } catch (IOException e) {
            throw new RuntimeException("Failed to read JSON file: " + jsonPath, e);
        }

        return fileId;
    }

    /**
     * Factory method that creates the {@link JSONObjectEntry} child for a JSON object root.
     *
     * <p>Subclasses may override this method to return a custom {@link JSONObjectEntry}
     * subclass, enabling the custom-root-factory pattern without changing parsing logic.
     *
     * @param fields   flat map of key-value pairs parsed from the root JSON object
     * @param parentId the identifier of this {@link JSONFileEntry} in the builder
     * @return a new (or custom) {@link JSONObjectEntry} to register as the root child
     */
    protected JSONObjectEntry createObjectRoot(Map<String, Object> fields, String parentId) {
        return new JSONObjectEntry(fields, parentId);
    }

    /**
     * Parses {@code content} and registers child entries under {@code parentId}.
     */
    private void parseAndAddChildren(EDRMBuilder builder, String content, String parentId) {
        if (content.startsWith("{")) {
            // Root is a JSON object
            JSONObject obj = new JSONObject(content);
            Map<String, Object> fields = jsonObjectToMap(obj);
            builder.addEntry(createObjectRoot(fields, parentId));

        } else if (content.startsWith("[")) {
            // Root is a JSON array — one JSONValueEntry per element
            JSONArray arr = new JSONArray(content);
            for (int i = 0; i < arr.length(); i++) {
                Object element = arr.isNull(i) ? null : arr.get(i);
                builder.addEntry(new JSONValueEntry(i, element, parentId));
            }

        } else {
            // Root is a scalar (string, number, boolean, or null)
            Object scalar = parseScalar(content);
            builder.addEntry(new JSONValueEntry(0, scalar, parentId));
        }
    }

    /**
     * Converts a {@link JSONObject} to a {@code Map<String, Object>} using Java
     * native types so that {@link MappingEntry} can assign the correct
     * {@link EntryField.Type} to each field.
     */
    private static Map<String, Object> jsonObjectToMap(JSONObject obj) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (String key : obj.keySet()) {
            if (obj.isNull(key)) {
                // MappingEntry.fillInitialFields calls v.toString(); use empty string for JSON null
                map.put(key, "");
            } else {
                Object val = obj.get(key);
                if (val instanceof JSONObject || val instanceof JSONArray) {
                    // Nested structure: store as its JSON string representation
                    map.put(key, val.toString());
                } else {
                    // Normalise numeric types: org.json may return BigDecimal or BigInteger
                    // (especially in newer versions). Convert them to Double/Long so that
                    // MappingEntry.fillInitialFields assigns the correct EntryField.Type.
                    if (val instanceof BigDecimal bd) {
                        val = bd.doubleValue();
                    } else if (val instanceof BigInteger bi) {
                        val = bi.longValue();
                    }
                    map.put(key, val);
                }
            }
        }
        return map;
    }

    /**
     * Parses a root-level scalar JSON token into the appropriate Java type.
     */
    private static Object parseScalar(String content) {
        if (content.equals("null"))  return null;
        if (content.equals("true"))  return Boolean.TRUE;
        if (content.equals("false")) return Boolean.FALSE;
        // Strip surrounding quotes for strings
        if (content.startsWith("\"") && content.endsWith("\"")) {
            return content.substring(1, content.length() - 1);
        }
        // Try numeric
        try {
            if (content.contains(".")) return Double.parseDouble(content);
            return Long.parseLong(content);
        } catch (NumberFormatException e) {
            return content;
        }
    }
}
