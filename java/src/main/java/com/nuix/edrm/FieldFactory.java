package com.nuix.edrm;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Assigns stable {@code field_N} XML attribute keys to human-readable field names.
 *
 * <h3>Static state and test isolation</h3>
 * {@code NAME_TO_KEY} and {@code NEXT_INDEX} are JVM-scoped singletons. Once a field name is
 * registered it always maps to the same {@code field_N} key within a JVM process. This is safe
 * because:
 * <ul>
 *   <li>{@code EntryInterface.fields} is keyed by <em>field name</em> (not by the generated key),
 *       so {@code getField("SHA-1")}, {@code getField("MIME Type")}, etc. are always resolved by
 *       name — they are completely independent of the generated key value.</li>
 *   <li>The generated key is only used as an EDRM XML attribute ({@code DocFieldID}); it never
 *       participates in any in-memory lookup that tests exercise.</li>
 * </ul>
 * Consequently, tests do not need a reset hook, and running tests in any order produces correct
 * results. The static counter does mean that {@code field_N} indices are not guaranteed to start
 * at 0 in every test method when tests share a JVM — but no test should assert on the exact
 * numeric suffix of a generated key.
 */
public class FieldFactory {
    private static final AtomicInteger NEXT_INDEX = new AtomicInteger(0);
    private static final Map<String, String> NAME_TO_KEY = new ConcurrentHashMap<>();

    private static String nextKey() {
        return "field_" + NEXT_INDEX.getAndIncrement();
    }

    /**
     * Returns an {@link EntryField} for the given field name, allocating a stable XML key on first
     * use. Subsequent calls with the same {@code fieldName} always receive the same key.
     */
    public static EntryField generateField(String fieldName, EntryField.Type fieldType, Object defaultValue) {
        String key = NAME_TO_KEY.computeIfAbsent(fieldName, k -> nextKey());
        return new EntryField(key, fieldName, fieldType, defaultValue);
    }
}