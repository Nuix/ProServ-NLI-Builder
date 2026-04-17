package com.nuix.edrm.datatypes;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.MappingEntry;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.StringJoiner;

/**
 * MappingEntry representing a JSON array.
 *
 * Simple scalar values are stored as fields (with their index string as the field name).
 * Complex values (nested arrays or objects) are added as child entries during addToBuilder().
 *
 * getText() returns a comma-separated string of the simple field values.
 * getName() returns the mapping name supplied at construction.
 *
 * Overridable generator hooks allow subclasses to substitute custom entry types for complex children:
 * <ul>
 *   <li>{@link #getChildArrayGenerator(String)} — for array children</li>
 *   <li>{@link #getChildObjectGenerator(String)} — for object children</li>
 * </ul>
 * Return null from any hook to use the default class.
 */
public class JSONArrayEntry extends MappingEntry {
    private final String mappingName;
    /** Entries that need to be added as children during addToBuilder() */
    private final List<Map.Entry<String, Object>> complexChildren = new ArrayList<>();
    /** Simple values, in order, for getText() */
    private final List<String> simpleValues = new ArrayList<>();

    public JSONArrayEntry(String mappingName, List<Object> array, String mimeType, String parentId) {
        super(buildSimpleMap(array), mimeType, parentId);
        this.mappingName = mappingName;
        partitionChildren(array);
    }

    /**
     * Builds a map of only the simple (scalar) entries from the array, keyed by string index.
     * Complex entries are excluded here and handled in addToBuilder().
     */
    private static Map<String, Object> buildSimpleMap(List<Object> array) {
        Map<String, Object> map = new LinkedHashMap<>();
        for (int i = 0; i < array.size(); i++) {
            Object v = array.get(i);
            if (isSimple(v)) {
                map.put(String.valueOf(i), v == null ? "" : v);
            }
        }
        return map;
    }

    /** Separate simple values (for simpleValues list) from complex ones (for complexChildren). */
    private void partitionChildren(List<Object> array) {
        for (int i = 0; i < array.size(); i++) {
            Object v = array.get(i);
            if (isSimple(v)) {
                simpleValues.add(v == null ? "" : String.valueOf(v));
            } else {
                complexChildren.add(Map.entry(String.valueOf(i), v));
            }
        }
    }

    private static boolean isSimple(Object v) {
        return !(v instanceof List) && !(v instanceof Map);
    }

    @Override
    public String getName() { return mappingName; }

    @Override
    public String getBaseName() { return mappingName; }

    /** Returns comma-separated string of simple field values. */
    @Override
    public String getText() {
        StringJoiner sj = new StringJoiner(", ");
        simpleValues.forEach(sj::add);
        return sj.toString();
    }

    /**
     * Adds this entry to the builder and then recursively adds all complex child entries.
     */
    @SuppressWarnings("unchecked")
    public String addToBuilder(EDRMBuilder builder) {
        builder.addEntry(this);
        String myId = getField(getIdentifierField()).getValue().toString();

        for (Map.Entry<String, Object> child : complexChildren) {
            String index = child.getKey();
            Object value = child.getValue();

            if (value instanceof List<?> listValue) {
                JSONArrayEntry childEntry = JsonEntryFactory.createArray(
                        index, (List<Object>) listValue, "application/x-json-array", myId,
                        getChildArrayGenerator(index));
                childEntry.addToBuilder(builder);
            } else if (value instanceof Map<?, ?> mapValue) {
                JSONObjectEntry childEntry = JsonEntryFactory.createObject(
                        index, (Map<String, Object>) mapValue, "application/x-json-object", myId,
                        getChildObjectGenerator(index));
                childEntry.addToBuilder(builder);
            }
        }

        return myId;
    }

    // --- Overridable generator hooks ---

    /** Return a factory for array children, or null for the default. */
    protected JsonEntryFactory.ArrayGenerator getChildArrayGenerator(String index) { return null; }

    /** Return a factory for object children, or null for the default. */
    protected JsonEntryFactory.ObjectGenerator getChildObjectGenerator(String index) { return null; }
}
