package com.nuix.edrm.datatypes;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EDRMUtilities;
import com.nuix.edrm.FileEntry;
import com.nuix.nli.CompoundEntry;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.Charset;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

public class CSVEntry extends FileEntry implements CompoundEntry {
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
        String csvEncoding = EDRMUtilities.EDRM_CONFIG.getOrDefault("csv_encoding", "UTF-8");
        Charset charset = Charset.forName(csvEncoding);
        try (BufferedReader reader = Files.newBufferedReader(path, charset)) {
            String header = reader.readLine();
            if (header == null) return;
            // Strip UTF-8 BOM (\uFEFF) if present as the first character of the header line
            if (!header.isEmpty() && header.charAt(0) == '\uFEFF') {
                header = header.substring(1);
            }
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