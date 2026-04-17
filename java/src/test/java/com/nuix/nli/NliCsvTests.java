package com.nuix.nli;

import com.nuix.edrm.datatypes.CSVEntry;
import com.nuix.edrm.datatypes.CSVRowEntry;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;

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

    // SLC-67: Structural CSV content tests

    @Test
    public void testRowCount() {
        // envars.csv has 17533 data rows (17534 total lines minus 1 header)
        Path envars = resources().resolve("envars.csv");
        CSVEntry entry = new CSVEntry(envars.toString());
        assertEquals(17533, entry.getData().size(),
                "envars.csv should have 17533 data rows (header excluded)");
    }

    @Test
    public void testFieldNames() {
        // All 6 CSV column headers must appear as field names on the CSVEntry
        Path envars = resources().resolve("envars.csv");
        CSVEntry entry = new CSVEntry(envars.toString());
        List<String> fields = entry.getRowFields();
        assertTrue(fields.contains("TreeDepth"), "Missing column: TreeDepth");
        assertTrue(fields.contains("PID"), "Missing column: PID");
        assertTrue(fields.contains("Process"), "Missing column: Process");
        assertTrue(fields.contains("Block"), "Missing column: Block");
        assertTrue(fields.contains("Variable"), "Missing column: Variable");
        assertTrue(fields.contains("Value"), "Missing column: Value");
        assertEquals(6, fields.size(), "Should have exactly 6 column headers");
    }

    @Test
    public void testFieldValues() {
        // Spot-check the first data row: TreeDepth=0, PID=784, Process=smss.exe,
        // Block=0x22c28202ce0, Variable=Path, Value=C:\Windows\System32
        Path envars = resources().resolve("envars.csv");
        CSVEntry entry = new CSVEntry(envars.toString());
        java.util.Map<String, String> firstRow = entry.getData().get(0);
        assertEquals("0", firstRow.get("TreeDepth"), "First row TreeDepth should be 0");
        assertEquals("784", firstRow.get("PID"), "First row PID should be 784");
        assertEquals("smss.exe", firstRow.get("Process"), "First row Process should be smss.exe");
        assertEquals("Path", firstRow.get("Variable"), "First row Variable should be Path");
        assertEquals("C:\\\\Windows\\\\System32", firstRow.get("Value"),
                "First row Value should be C:\\\\Windows\\\\System32 (literal double-backslash as stored in CSV)");
    }

    @Test
    public void testCustomRowName() {
        // EnvEntry subclass should compose getName() as "(PID) Process [Variable]"
        Path envars = resources().resolve("envars.csv");
        // Use the single-argument constructor; the row generator is not exercised in this test
        // (EnvEntry is constructed directly below for the assertion).
        CSVEntry entry = new CSVEntry(envars.toString());
        // First row: PID=784, Process=smss.exe, Variable=Path
        CSVRowEntry firstRow = new EnvEntry(entry, 0);
        assertEquals("(784) smss.exe [Path]", firstRow.getName(),
                "EnvEntry getName() should return '(PID) Process [Variable]' format");
    }

    @Test
    public void testBomStripping() throws IOException {
        // Create a CSV with a UTF-8 BOM prefix; headers must be parsed without the BOM character
        Path tempCsv = Files.createTempFile("bom_stripping_test", ".csv");
        try {
            // Write a BOM followed by CSV content
            byte[] bom = new byte[]{(byte) 0xEF, (byte) 0xBB, (byte) 0xBF};
            byte[] body = "ColA,ColB\nval1,val2".getBytes(StandardCharsets.UTF_8);
            byte[] content = new byte[bom.length + body.length];
            System.arraycopy(bom, 0, content, 0, bom.length);
            System.arraycopy(body, 0, content, bom.length, body.length);
            Files.write(tempCsv, content);

            CSVEntry entry = new CSVEntry(tempCsv.toString());

            List<String> fields = entry.getRowFields();
            assertFalse(fields.isEmpty(), "Should have parsed header columns from BOM-prefixed CSV");
            assertFalse(fields.get(0).startsWith("\uFEFF"),
                    "First column header must not start with BOM character \\uFEFF");
            assertEquals("ColA", fields.get(0),
                    "First column header should be 'ColA' without any BOM prefix");
            assertEquals("ColB", fields.get(1),
                    "Second column header should be 'ColB'");
            assertEquals(1, entry.getData().size(),
                    "Should have parsed exactly 1 data row");
        } finally {
            Files.deleteIfExists(tempCsv);
        }
    }
}
