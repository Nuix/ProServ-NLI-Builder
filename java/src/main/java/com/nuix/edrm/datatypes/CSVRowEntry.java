package com.nuix.edrm.datatypes;

import com.nuix.edrm.EntryField;
import com.nuix.edrm.FieldFactory;
import com.nuix.edrm.MappingEntry;

import java.util.Map;

public class CSVRowEntry extends MappingEntry {
    protected final CSVEntry parentCsv;
    protected final int rowIndex;

    public CSVRowEntry(CSVEntry parentCsv, int rowIndex) {
        super(Map.of(), "application/x-database-table-row", parentCsv.getField("SHA-1").getValue().toString());
        this.parentCsv = parentCsv;
        this.rowIndex = rowIndex;
        // populate fields from CSV headers
        for (String f : parentCsv.getRowFields()) {
            Object v = getData().getOrDefault(f, parentCsv.getData().get(rowIndex).get(f));
            putField(FieldFactory.generateField(f, EntryField.Type.Text, v));
        }
        // Provide a default Name using a common field if it exists
        String name = getName();
        setFieldValue("Name", name);
    }

    public CSVEntry getParentCsv() { return parentCsv; }

    public String getName() {
        // Try to make a readable name; default to first field
        if (!parentCsv.getRowFields().isEmpty()) {
            String first = parentCsv.getRowFields().get(0);
            Object v = parentCsv.getData().get(rowIndex).get(first);
            return String.valueOf(v);
        }
        return "Row " + rowIndex;
    }

    @Override public String addAsParentPath(String existingPath) { return getName() + "/" + existingPath; }

    @Override public String getIdentifierField() { return "Id"; }
}