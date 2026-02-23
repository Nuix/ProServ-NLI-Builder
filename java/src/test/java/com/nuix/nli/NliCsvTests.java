package com.nuix.nli;

import com.nuix.edrm.datatypes.CSVEntry;
import com.nuix.edrm.datatypes.CSVRowEntry;
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
                String pid = String.valueOf(getField("PID").getValue());
                String process = String.valueOf(getField("Process").getValue());
                String variable = String.valueOf(getField("Variable").getValue());
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