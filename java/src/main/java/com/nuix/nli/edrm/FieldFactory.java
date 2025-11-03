package com.nuix.nli.edrm;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

public class FieldFactory {
    private static final AtomicInteger NEXT_INDEX = new AtomicInteger(0);
    private static final Map<String, String> NAME_TO_KEY = new ConcurrentHashMap<>();

    private static String nextKey() {
        return "field_" + NEXT_INDEX.getAndIncrement();
    }

    public static EntryField generateField(String fieldName, EntryField.Type fieldType, Object defaultValue) {
        String key = NAME_TO_KEY.computeIfAbsent(fieldName, k -> nextKey());
        return new EntryField(key, fieldName, fieldType, defaultValue);
    }
}