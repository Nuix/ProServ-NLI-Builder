package com.nuix.edrm.datatypes;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.FieldFactory;
import com.nuix.edrm.MappingEntry;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * MappingEntry representing a scalar JSON leaf node (string, number, boolean, null).
 * Type detection is performed at construction time:
 * <ul>
 *   <li>Boolean → EntryField.Type.Boolean</li>
 *   <li>Integer/Long → EntryField.Type.LongInteger</li>
 *   <li>Double/Float → EntryField.Type.Decimal</li>
 *   <li>String matching ISO 8601 via OffsetDateTime.parse() → EntryField.Type.DateTime</li>
 *   <li>All others → EntryField.Type.Text</li>
 * </ul>
 */
public class JSONValueEntry extends MappingEntry {
    private final String mappingName;
    private final Object scalarValue;

    public JSONValueEntry(String mappingName, String keyName, Object value, String mimeType, String parentId) {
        super(buildMap(keyName, value), mimeType, parentId);
        this.mappingName = mappingName;
        this.scalarValue = value;
        // Override the type for the key field based on value type
        overrideFieldType(keyName, value);
    }

    private static Map<String, Object> buildMap(String keyName, Object value) {
        Map<String, Object> map = new LinkedHashMap<>();
        map.put(keyName, value == null ? "" : value);
        return map;
    }

    /**
     * After MappingEntry's fillInitialFields runs (which uses instanceof checks too),
     * we re-check for ISO 8601 strings to correctly classify DateTime values that would
     * otherwise be stored as Text.
     */
    private void overrideFieldType(String keyName, Object value) {
        if (value instanceof String str && !str.isEmpty()) {
            try {
                OffsetDateTime.parse(str);
                // It parsed — re-register this field with DateTime type
                putField(FieldFactory.generateField(keyName, EntryField.Type.DateTime, value));
            } catch (Exception ignored) {
                // Not a datetime — keep the Text type that fillInitialFields assigned
            }
        }
    }

    /**
     * Returns the mapping name supplied at construction, overriding MappingEntry's
     * data-derived name logic.
     */
    @Override
    public String getName() {
        return mappingName;
    }

    @Override
    public String getBaseName() {
        return mappingName;
    }

    /**
     * Returns the string representation of the scalar value.
     */
    @Override
    public String getText() {
        return scalarValue == null ? "" : String.valueOf(scalarValue);
    }

    /**
     * Adds this entry to the builder. JSONValueEntry is a leaf — no children.
     */
    public String addToBuilder(EDRMBuilder builder) {
        builder.addEntry(this);
        return getField(getIdentifierField()).getValue().toString();
    }
}
