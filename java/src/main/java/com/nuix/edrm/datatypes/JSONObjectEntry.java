package com.nuix.edrm.datatypes;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.MappingEntry;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * MappingEntry representing a JSON object (key/value pairs).
 *
 * Simple scalar values are stored as fields on this entry.
 * Complex values (nested arrays or objects) are added as child entries during addToBuilder().
 *
 * getText() returns "key=value\n" for all simple fields (same format as MappingEntry).
 * getName() returns the mapping name supplied at construction.
 *
 * Overridable generator hooks allow subclasses to substitute custom entry types for complex children:
 * <ul>
 *   <li>{@link #getChildArrayGenerator(String)} — for array children</li>
 *   <li>{@link #getChildObjectGenerator(String)} — for object children</li>
 * </ul>
 * Return null from any hook to use the default class.
 */
public class JSONObjectEntry extends MappingEntry {
    private final String mappingName;
    /** Complex child entries to be added during addToBuilder() */
    private final List<Map.Entry<String, Object>> complexChildren = new ArrayList<>();

    public JSONObjectEntry(String mappingName, Map<String, Object> object, String mimeType, String parentId) {
        super(buildSimpleMap(object), mimeType, parentId);
        this.mappingName = mappingName;
        partitionChildren(object);
    }

    /**
     * Extracts only scalar key/value pairs from the JSON object for the parent MappingEntry.
     */
    private static Map<String, Object> buildSimpleMap(Map<String, Object> object) {
        Map<String, Object> map = new LinkedHashMap<>();
        if (object != null) {
            object.forEach((k, v) -> {
                if (isSimple(v)) {
                    map.put(k, v == null ? "" : v);
                }
            });
        }
        return map;
    }

    /** Separates complex values into the complexChildren list. */
    private void partitionChildren(Map<String, Object> object) {
        if (object == null) return;
        object.forEach((k, v) -> {
            if (!isSimple(v)) {
                complexChildren.add(Map.entry(k, v));
            }
        });
    }

    private static boolean isSimple(Object v) {
        return !(v instanceof List) && !(v instanceof Map);
    }

    @Override
    public String getName() { return mappingName; }

    @Override
    public String getBaseName() { return mappingName; }

    /**
     * Adds this entry to the builder and then recursively adds all complex child entries.
     */
    @SuppressWarnings("unchecked")
    public String addToBuilder(EDRMBuilder builder) {
        builder.addEntry(this);
        String myId = getField(getIdentifierField()).getValue().toString();

        for (Map.Entry<String, Object> child : complexChildren) {
            String key = child.getKey();
            Object value = child.getValue();

            if (value instanceof List<?> listValue) {
                JSONArrayEntry childEntry = JsonEntryFactory.createArray(
                        key, (List<Object>) listValue, "application/x-json-array", myId,
                        getChildArrayGenerator(key));
                childEntry.addToBuilder(builder);
            } else if (value instanceof Map<?, ?> mapValue) {
                JSONObjectEntry childEntry = JsonEntryFactory.createObject(
                        key, (Map<String, Object>) mapValue, "application/x-json-object", myId,
                        getChildObjectGenerator(key));
                childEntry.addToBuilder(builder);
            }
        }

        return myId;
    }

    // --- Overridable generator hooks ---

    /** Return a custom subclass to use for array children, or null for the default. */
    protected Class<? extends JSONArrayEntry> getChildArrayGenerator(String key) { return null; }

    /** Return a custom subclass to use for object children, or null for the default. */
    protected Class<? extends JSONObjectEntry> getChildObjectGenerator(String key) { return null; }
}
