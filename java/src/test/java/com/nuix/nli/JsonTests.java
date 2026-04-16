package com.nuix.nli;

import com.nuix.edrm.datatypes.JSONFileEntry;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.assertTrue;

public class JsonTests {
    private Path resources() { return Paths.get("..", "python", "test", "resources").toAbsolutePath().normalize(); }
    private Path outputDir() { return Paths.get("build", "test-output", "json").toAbsolutePath().normalize(); }

    private void ensureOutputDir() {
        if (!outputDir().toFile().exists()) outputDir().toFile().mkdirs();
    }

    // --- original test ---

    @Test
    public void testSimpleStr() {
        Path json = resources().resolve("simple_str.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        ensureOutputDir();
        Path out = outputDir().resolve("simple_str.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }

    // --- scalar root types ---

    /**
     * Root-level JSON string whose text begins with a '[' character.
     * With the old startsWith heuristic this would have been misidentified
     * as an array root and caused a JSONException.  With JSONTokener-based
     * detection it is correctly handled as a scalar string.
     */
    @Test
    public void testStringRootLooksLikeArray() throws Exception {
        Path tmp = Files.createTempFile("slc149-test-", ".json");
        try {
            // Legal JSON: a root-level string that begins with '['
            Files.writeString(tmp, "\"[not an array]\"");
            JSONFileEntry entry = new JSONFileEntry(tmp.toString());
            NLIGenerator nli = new NLIGenerator();
            nli.addEntry(entry);
            ensureOutputDir();
            Path out = outputDir().resolve("string_looks_like_array.nli");
            nli.save(out);
            assertTrue(Files.exists(out));
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    /**
     * Root-level JSON string whose text begins with a '{' character.
     * Same class of defect as the array case above.
     */
    @Test
    public void testStringRootLooksLikeObject() throws Exception {
        Path tmp = Files.createTempFile("slc149-test-", ".json");
        try {
            Files.writeString(tmp, "\"{not an object}\"");
            JSONFileEntry entry = new JSONFileEntry(tmp.toString());
            NLIGenerator nli = new NLIGenerator();
            nli.addEntry(entry);
            ensureOutputDir();
            Path out = outputDir().resolve("string_looks_like_object.nli");
            nli.save(out);
            assertTrue(Files.exists(out));
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    @Test
    public void testSimpleInt() {
        Path json = resources().resolve("simple_int.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        ensureOutputDir();
        Path out = outputDir().resolve("simple_int.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }

    @Test
    public void testSimpleFloat() {
        Path json = resources().resolve("simple_float.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        ensureOutputDir();
        Path out = outputDir().resolve("simple_float.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }

    @Test
    public void testSimpleBoolean() {
        Path json = resources().resolve("simple_boolean.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        ensureOutputDir();
        Path out = outputDir().resolve("simple_boolean.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }

    // --- object root types ---

    @Test
    public void testObjectMixed() {
        Path json = resources().resolve("object_mixed.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        ensureOutputDir();
        Path out = outputDir().resolve("object_mixed.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }

    @Test
    public void testObjectComplex() {
        Path json = resources().resolve("object_complex.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        ensureOutputDir();
        Path out = outputDir().resolve("object_complex.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }

    // --- array root type ---

    @Test
    public void testListMixed() {
        Path json = resources().resolve("list_mixed.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        ensureOutputDir();
        Path out = outputDir().resolve("list_mixed.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }
}
