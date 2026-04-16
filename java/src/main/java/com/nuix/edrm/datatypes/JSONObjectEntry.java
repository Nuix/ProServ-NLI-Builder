package com.nuix.edrm.datatypes;

import com.nuix.edrm.EntryField;
import com.nuix.edrm.FieldFactory;
import com.nuix.edrm.MappingEntry;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Represents a JSON object as a structured EDRM mapping entry.
 * Each key-value pair in the JSON object becomes a typed field.
 */
public class JSONObjectEntry extends MappingEntry {

    /**
     * Constructs a JSONObjectEntry from a flat map of typed values.
     *
     * @param fields   the key-value pairs parsed from the JSON object
     * @param parentId the identifier of the parent JSONFileEntry
     */
    public JSONObjectEntry(Map<String, Object> fields, String parentId) {
        super(fields, "application/x-json-object", parentId);
    }

    /**
     * Returns the number of data fields (excluding the synthetic metadata fields
     * such as MIME Type, Name, SHA-1, and Item Date that are added by MappingEntry).
     */
    public int getDataFieldCount() {
        return data.size();
    }
}
