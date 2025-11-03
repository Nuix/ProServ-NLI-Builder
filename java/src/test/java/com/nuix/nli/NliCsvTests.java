package com.nuix.nli;

import com.nuix.nli.datatypes.CSVEntry;
import com.nuix.nli.datatypes.CSVRowEntry;
import com.nuix.nli.nli.NLIGenerator;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.assertTrue;

public class NliCsvTests {
    private Path resources() { return Paths.get("..", "python", "test", "resources").toAbsolutePath().normalize(); }
    private Path outputDir() { return Paths.get("build", "test-output").toAbsolutePath().normalize(); }

    public static class EnvEntry extends CSVRowEntry {
        public EnvEntry(CSVEntry parent, int idx) { super(parent, idx); }
        @Override public String getName() {
            // If fields exist, build a composed name, else fallback
            try {
                String pid = String.valueOf(get("PID").getValue());
                String process = String.valueOf(get("Process").getValue());
                String variable = String.valueOf(get("Variable").getValue());
                return "("+pid+") "+process+" ["+variable+"]";
            } catch (Exception e) {
                return super.getName();
            }
        }
    }

    @Test
    public void testBaseCsvToNli() {
        Path envars = resources().resolve("envars.csv");
        CSVEntry entry = new CSVEntry(envars.toString());
        NLIGenerator gen = new NLIGenerator();
        gen.addEntry(entry);
        Path out = outputDir().resolve("csv_test.nli");
        gen.save(out);
        assertTrue(Files.exists(out));
    }
}