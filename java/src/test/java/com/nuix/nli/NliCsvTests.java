package com.nuix.nli;

import com.nuix.edrm.datatypes.CSVEntry;
import com.nuix.edrm.datatypes.CSVRowEntry;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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

    @Test
    public void testBomPrefixedCsv() throws IOException {
        // Create a temp CSV with a UTF-8 BOM prefix (as produced by Microsoft Excel)
        Path tempCsv = Files.createTempFile("bom_test", ".csv");
        try {
            String content = "\uFEFFName,Value\nAlpha,1\nBeta,2";
            Files.writeString(tempCsv, content, StandardCharsets.UTF_8);

            CSVEntry entry = new CSVEntry(tempCsv.toString());

            assertFalse(entry.getRowFields().isEmpty(), "Should have parsed header columns");
            assertFalse(entry.getRowFields().get(0).startsWith("\uFEFF"),
                    "First column header must not start with BOM character");
            assertEquals("Name", entry.getRowFields().get(0),
                    "First column header should be 'Name' without BOM prefix");
            assertEquals("Value", entry.getRowFields().get(1),
                    "Second column header should be 'Value'");
            assertEquals(2, entry.getData().size(),
                    "Should have parsed 2 data rows");
        } finally {
            Files.deleteIfExists(tempCsv);
        }
    }

    @Test
    public void testPlainUtf8CsvUnaffected() throws IOException {
        // Verify plain UTF-8 CSV (no BOM) still parses correctly
        Path tempCsv = Files.createTempFile("plain_utf8_test", ".csv");
        try {
            String content = "Name,Value\nGamma,3\nDelta,4";
            Files.writeString(tempCsv, content, StandardCharsets.UTF_8);

            CSVEntry entry = new CSVEntry(tempCsv.toString());

            assertEquals("Name", entry.getRowFields().get(0),
                    "First column header should be 'Name'");
            assertEquals(2, entry.getData().size(),
                    "Should have parsed 2 data rows");
        } finally {
            Files.deleteIfExists(tempCsv);
        }
    }
}