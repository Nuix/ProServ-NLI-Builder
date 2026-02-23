package com.nuix.edrm.datatypes;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.FileEntry;
import com.nuix.edrm.MappingEntry;
import com.nuix.nli.CompoundEntry;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;

public class JSONFileEntry extends FileEntry implements CompoundEntry {
    private final Path jsonPath;

    public JSONFileEntry(String jsonFilePath) { this(jsonFilePath, "application/json", null); }

    public JSONFileEntry(String jsonFilePath, String mimeType, String parentId) {
        super(jsonFilePath, mimeType, parentId);
        this.jsonPath = Path.of(jsonFilePath).toAbsolutePath();
    }

    public String addToBuilder(EDRMBuilder builder) {
        builder.addEntry(this);
        // Minimal behavior: attach a single mapping child with the entire JSON as text
        try {
            String content = Files.readString(jsonPath);
            Map<String,Object> map = new LinkedHashMap<>();
            map.put("json", content);
            builder.addEntry(new MappingEntry(map, "application/x-json-value", getField(getIdentifierField()).getValue().toString()));
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
        return getField(getIdentifierField()).getValue().toString();
    }
}