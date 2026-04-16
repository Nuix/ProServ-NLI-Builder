package com.nuix.edrm.datatypes;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.FileEntry;
import com.nuix.edrm.MappingEntry;
import com.nuix.nli.CompoundEntry;
import org.json.JSONArray;
import org.json.JSONObject;
import org.json.JSONTokener;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * FileEntry implementation for JSON documents.
 *
 * <p>The root JSON type is determined using {@link JSONTokener} rather than
 * inspecting the first character of the raw content string.  Relying on
 * {@code content.startsWith("{")} / {@code content.startsWith("[")} is brittle:
 * a legal root-level JSON string whose text begins with '{' or '[' (e.g.
 * {@code "[not an array]"}) would be misidentified and cause a parse error.
 * {@code JSONTokener} reads the actual first token and returns the correct
 * Java type, so any legal JSON document is handled correctly.</p>
 */
public class JSONFileEntry extends FileEntry implements CompoundEntry {
    private final Path jsonPath;

    public JSONFileEntry(String jsonFilePath) { this(jsonFilePath, "application/json", null); }

    public JSONFileEntry(String jsonFilePath, String mimeType, String parentId) {
        super(jsonFilePath, mimeType, parentId);
        this.jsonPath = Path.of(jsonFilePath).toAbsolutePath();
    }

    /**
     * Parse the JSON file and add child entries to the builder.
     *
     * <p>Type detection is performed by {@link JSONTokener#nextValue()}, which
     * returns a {@link JSONObject}, {@link JSONArray}, or a boxed primitive /
     * {@link String} depending on the actual root token — not on the first
     * character of the raw content string.</p>
     *
     * @param builder the EDRM builder to add child entries into
     * @param parentId the identifier of the parent entry (this file entry)
     */
    private void parseAndAddChildren(EDRMBuilder builder, String parentId) {
        String content;
        try {
            content = Files.readString(jsonPath);
        } catch (IOException e) {
            throw new RuntimeException("Failed to read JSON file: " + jsonPath, e);
        }

        // Use JSONTokener to determine the actual root type.  This correctly
        // handles any legal JSON document, including root-level strings whose
        // content begins with '{' or '['.
        Object root = new JSONTokener(content).nextValue();

        if (root instanceof JSONObject jsonObject) {
            Map<String, Object> map = new LinkedHashMap<>();
            for (String key : jsonObject.keySet()) {
                map.put(key, jsonObject.get(key).toString());
            }
            builder.addEntry(new MappingEntry(map, "application/x-json-object", parentId));

        } else if (root instanceof JSONArray jsonArray) {
            Map<String, Object> map = new LinkedHashMap<>();
            for (int i = 0; i < jsonArray.length(); i++) {
                map.put(String.valueOf(i), jsonArray.get(i).toString());
            }
            builder.addEntry(new MappingEntry(map, "application/x-json-array", parentId));

        } else {
            // Scalar value: string, number, boolean, or null.
            // root is already a correctly decoded Java object (String, Integer,
            // Long, Double, Boolean, or JSONObject.NULL) — no manual substring
            // stripping needed.
            Map<String, Object> map = new LinkedHashMap<>();
            map.put("Value", root == JSONObject.NULL ? null : root.toString());
            builder.addEntry(new MappingEntry(map, "application/x-json-value", parentId));
        }
    }

    public String addToBuilder(EDRMBuilder builder) {
        builder.addEntry(this);
        String myId = getField(getIdentifierField()).getValue().toString();
        parseAndAddChildren(builder, myId);
        return myId;
    }
}
