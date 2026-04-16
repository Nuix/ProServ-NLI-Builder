package com.nuix.edrm.datatypes;

import com.nuix.edrm.MappingEntry;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Represents a single JSON value (scalar or array element) as an EDRM mapping entry.
 * Used when a JSON file contains a top-level array or when individual values need
 * to be surfaced as discrete entries with a parent relationship.
 */
public class JSONValueEntry extends MappingEntry {

    private final Object rawValue;

    /**
     * @param index    zero-based position of this value within the parent array
     * @param value    the parsed Java object (String, Integer, Long, Double, Boolean, or null)
     * @param parentId identifier of the owning JSONFileEntry
     */
    public JSONValueEntry(int index, Object value, String parentId) {
        super(buildMap(index, value), "application/x-json-value", parentId);
        this.rawValue = value;
    }

    private static Map<String, Object> buildMap(int index, Object value) {
        Map<String, Object> map = new LinkedHashMap<>();
        // Use a stable key so tests can reference it
        map.put("index", (long) index);
        map.put("value", value == null ? "" : value.toString());
        return map;
    }

    /** Returns the raw Java value parsed from JSON (may be null for JSON null). */
    public Object getRawValue() {
        return rawValue;
    }
}
