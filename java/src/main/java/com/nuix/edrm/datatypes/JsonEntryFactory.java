package com.nuix.edrm.datatypes;

import java.util.List;
import java.util.Map;

/**
 * Package-private factory that instantiates JSON entry types, respecting subclass overrides.
 * <p>
 * Each {@code create*} method accepts a nullable {@link FunctionalInterface} generator. When a
 * generator is supplied it is invoked directly — no reflection, full compile-time safety. When
 * the generator is {@code null} the default class is constructed directly.
 */
class JsonEntryFactory {

    /** Factory for {@link JSONValueEntry} subclasses. */
    @FunctionalInterface
    interface ValueGenerator {
        JSONValueEntry create(String mappingName, String keyName, Object value,
                              String mimeType, String parentId);
    }

    /** Factory for {@link JSONArrayEntry} subclasses. */
    @FunctionalInterface
    interface ArrayGenerator {
        JSONArrayEntry create(String name, List<Object> array, String mimeType, String parentId);
    }

    /** Factory for {@link JSONObjectEntry} subclasses. */
    @FunctionalInterface
    interface ObjectGenerator {
        JSONObjectEntry create(String name, Map<String, Object> object, String mimeType, String parentId);
    }

    static JSONValueEntry createValue(
            String mappingName,
            String keyName,
            Object value,
            String mimeType,
            String parentId,
            ValueGenerator generator) {

        if (generator != null) {
            return generator.create(mappingName, keyName, value, mimeType, parentId);
        }
        return new JSONValueEntry(mappingName, keyName, value, mimeType, parentId);
    }

    static JSONArrayEntry createArray(
            String name,
            List<Object> array,
            String mimeType,
            String parentId,
            ArrayGenerator generator) {

        if (generator != null) {
            return generator.create(name, array, mimeType, parentId);
        }
        return new JSONArrayEntry(name, array, mimeType, parentId);
    }

    static JSONObjectEntry createObject(
            String name,
            Map<String, Object> object,
            String mimeType,
            String parentId,
            ObjectGenerator generator) {

        if (generator != null) {
            return generator.create(name, object, mimeType, parentId);
        }
        return new JSONObjectEntry(name, object, mimeType, parentId);
    }
}
