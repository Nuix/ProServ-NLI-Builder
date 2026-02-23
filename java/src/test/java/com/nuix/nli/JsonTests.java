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

    @Test
    public void testSimpleStr() {
        Path json = resources().resolve("simple_str.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        if (outputDir().toFile().exists() == false) outputDir().toFile().mkdirs();
        Path out = outputDir().resolve("simple_str.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }
}