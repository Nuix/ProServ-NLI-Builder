package com.nuix.nli.datatypes;

import com.nuix.nli.edrm.EDRMBuilder;
import com.nuix.nli.edrm.FileEntry;
import com.nuix.nli.edrm.MappingEntry;
import com.nuix.nli.nli.CompoundEnty;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

public class CSVEntry extends FileEntry implements CompoundEnty {
    private final List<Map<String, String>> data = new ArrayList<>();
    private final List<String> rowFields = new ArrayList<>();
    private final RowGenerator rowGenerator;

    @FunctionalInterface
    public interface RowGenerator { CSVRowEntry create(CSVEntry parent, int rowIndex); }

    public CSVEntry(String filePath) { this(filePath, "text/csv", null, null, ','); }

    public CSVEntry(String filePath, String mimeType, String parentId, RowGenerator rowGenerator, char delimiter) {
        super(filePath, mimeType, parentId);
        this.rowGenerator = rowGenerator;
        load(Paths.get(filePath), delimiter);
    }

    private void load(Path path, char delimiter) {
        try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            String header = reader.readLine();
            if (header == null) return;
            String[] headers = header.split(String.valueOf(delimiter));
            for (String h : headers) {
                String t = h.trim();
                if (!t.isEmpty()) rowFields.add(t);
            }
            String line;
            while ((line = reader.readLine()) != null) {
                String[] parts = line.split(String.valueOf(delimiter), -1);
                Map<String, String> row = new LinkedHashMap<>();
                for (int i = 0; i < rowFields.size() && i < parts.length; i++) {
                    row.put(rowFields.get(i), parts[i]);
                }
                data.add(row);
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    public List<Map<String, String>> getData() { return data; }
    public List<String> getRowFields() { return rowFields; }

    public String addToBuilder(EDRMBuilder builder) {
        builder.addEntry(this);
        RowGenerator gen = (rowGenerator != null) ? rowGenerator : CSVRowEntry::new;
        for (int i = 0; i < data.size(); i++) {
            builder.addEntry(gen.create(this, i));
        }
        return getField(getIdentifierField()).getValue().toString();
    }
}