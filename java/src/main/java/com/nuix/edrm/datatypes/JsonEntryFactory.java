package com.nuix.edrm.datatypes;

import java.lang.reflect.Constructor;
import java.util.List;
import java.util.Map;

/**
 * Package-private factory that instantiates JSON entry types, respecting subclass overrides.
 * When a custom generator class is provided it is reflectively instantiated; otherwise the
 * default class is used directly.
 */
class JsonEntryFactory {

    static JSONValueEntry createValue(
            String mappingName,
            String keyName,
            Object value,
            String mimeType,
            String parentId,
            Class<? extends JSONValueEntry> generatorClass) {

        if (generatorClass != null) {
            try {
                @SuppressWarnings("unchecked") // getConstructor returns raw Constructor; cast to typed form is safe here
                Constructor<? extends JSONValueEntry> ctor =
                        (Constructor<? extends JSONValueEntry>) generatorClass.getConstructor(String.class, String.class, Object.class, String.class, String.class);
                return ctor.newInstance(mappingName, keyName, value, mimeType, parentId);
            } catch (ReflectiveOperationException e) {
                throw new RuntimeException("Failed to instantiate custom JSONValueEntry subclass: " + generatorClass.getName(), e);
            }
        }
        return new JSONValueEntry(mappingName, keyName, value, mimeType, parentId);
    }

    static JSONArrayEntry createArray(
            String name,
            List<Object> array,
            String mimeType,
            String parentId,
            Class<? extends JSONArrayEntry> generatorClass) {

        if (generatorClass != null) {
            try {
                @SuppressWarnings("unchecked") // getConstructor returns raw Constructor; cast to typed form is safe here
                Constructor<? extends JSONArrayEntry> ctor =
                        (Constructor<? extends JSONArrayEntry>) generatorClass.getConstructor(String.class, List.class, String.class, String.class);
                return ctor.newInstance(name, array, mimeType, parentId);
            } catch (ReflectiveOperationException e) {
                throw new RuntimeException("Failed to instantiate custom JSONArrayEntry subclass: " + generatorClass.getName(), e);
            }
        }
        return new JSONArrayEntry(name, array, mimeType, parentId);
    }

    static JSONObjectEntry createObject(
            String name,
            Map<String, Object> object,
            String mimeType,
            String parentId,
            Class<? extends JSONObjectEntry> generatorClass) {

        if (generatorClass != null) {
            try {
                @SuppressWarnings("unchecked") // getConstructor returns raw Constructor; cast to typed form is safe here
                Constructor<? extends JSONObjectEntry> ctor =
                        (Constructor<? extends JSONObjectEntry>) generatorClass.getConstructor(String.class, Map.class, String.class, String.class);
                return ctor.newInstance(name, object, mimeType, parentId);
            } catch (ReflectiveOperationException e) {
                throw new RuntimeException("Failed to instantiate custom JSONObjectEntry subclass: " + generatorClass.getName(), e);
            }
        }
        return new JSONObjectEntry(name, object, mimeType, parentId);
    }
}
