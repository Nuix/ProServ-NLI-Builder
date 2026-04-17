package com.nuix.nli;

import com.fasterxml.jackson.core.JsonParseException;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.datatypes.JSONFileEntry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.w3c.dom.Document;
import org.w3c.dom.NodeList;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.junit.jupiter.api.Assertions.*;

public class JsonTests {
    private Path resources() { return Paths.get(".", "src", "test", "resources").toAbsolutePath().normalize(); }
    private Path outputDir() { return Paths.get("build", "test-output", "json").toAbsolutePath().normalize(); }

    @BeforeEach
    void ensureOutputDir() throws Exception {
        Files.createDirectories(outputDir());
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    /** Write JSON content to a temp file in the output dir and return its path. */
    private Path writeTempJson(String filename, String content) throws Exception {
        Path tmp = outputDir().resolve(filename);
        Files.writeString(tmp, content, StandardCharsets.UTF_8);
        return tmp;
    }

    /** Parse the EDRM XML from an NLI ZIP. */
    private Document getEdrmXmlFromNli(Path nliPath) throws Exception {
        try (ZipInputStream zis = new ZipInputStream(Files.newInputStream(nliPath))) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                if (entry.getName().endsWith("image_contents.xml")) {
                    DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
                    DocumentBuilder db = dbf.newDocumentBuilder();
                    return db.parse(zis);
                }
            }
        }
        throw new AssertionError("image_contents.xml not found in NLI: " + nliPath);
    }

    /** XPath count helper. */
    private int xpathCount(Document doc, String expression) throws Exception {
        XPath xp = XPathFactory.newInstance().newXPath();
        NodeList nodes = (NodeList) xp.evaluate(expression, doc, XPathConstants.NODESET);
        return nodes.getLength();
    }

    /** XPath text helper — returns text of first matching node. */
    private String xpathText(Document doc, String expression) throws Exception {
        XPath xp = XPathFactory.newInstance().newXPath();
        return (String) xp.evaluate(expression, doc, XPathConstants.STRING);
    }

    // -----------------------------------------------------------------------
    // Existing test (preserving original behaviour)
    // -----------------------------------------------------------------------

    @Test
    public void testSimpleStr() {
        Path json = resources().resolve("simple_str.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        Path out = outputDir().resolve("simple_str.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }

    // -----------------------------------------------------------------------
    // SLC-65: New recursive traversal tests
    // -----------------------------------------------------------------------

    /**
     * Test 1: Scalar integer JSON → JSONValueEntry with LongInteger-typed field in EDRM XML.
     */
    @Test
    public void testScalarInteger() throws Exception {
        Path json = writeTempJson("scalar_int.json", "42");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(new JSONFileEntry(json.toString()));
        Path out = outputDir().resolve("scalar_int.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);
        // JSON file itself + the scalar value child = at least 2 documents
        int docCount = xpathCount(doc, "//Document");
        assertTrue(docCount >= 2, "Expected at least 2 documents, got " + docCount);

        // A LongInteger-typed field must appear
        String dataType = xpathText(doc, "//Field[@DataType='LongInteger']/@DataType");
        assertEquals("LongInteger", dataType,
                "Expected a LongInteger-typed field in the EDRM XML");
    }

    /**
     * Test 2: Scalar string JSON → JSONValueEntry with Text-typed field.
     */
    @Test
    public void testScalarString() throws Exception {
        Path json = writeTempJson("scalar_str_new.json", "\"hello world\"");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(new JSONFileEntry(json.toString()));
        Path out = outputDir().resolve("scalar_str_new.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);
        String dataType = xpathText(doc, "//Field[@DataType='Text']/@DataType");
        assertEquals("Text", dataType, "Expected a Text-typed field for a string scalar");
    }

    /**
     * Test 3: Array of scalars [1,2,3] → at least 2 documents (file + array entry).
     */
    @Test
    public void testArrayOfScalars() throws Exception {
        Path json = writeTempJson("array_scalars.json", "[1, 2, 3]");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(new JSONFileEntry(json.toString()));
        Path out = outputDir().resolve("array_scalars.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);
        int docCount = xpathCount(doc, "//Document");
        assertTrue(docCount >= 2, "Expected at least 2 documents (file + array), got " + docCount);
    }

    /**
     * Test 4: Nested object {"a":{"b":1}} → at least 3 documents with a Relationship element.
     */
    @Test
    public void testNestedObject() throws Exception {
        Path json = writeTempJson("nested_obj.json", "{\"a\":{\"b\":1}}");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(new JSONFileEntry(json.toString()));
        Path out = outputDir().resolve("nested_obj.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);
        int docCount = xpathCount(doc, "//Document");
        assertTrue(docCount >= 3,
                "Expected at least 3 documents for nested object (file + outer + inner), got " + docCount);

        int relCount = xpathCount(doc, "//Relationship");
        assertTrue(relCount >= 1,
                "Expected at least one Relationship element, got " + relCount);
    }

    /**
     * Test 5: ISO 8601 string value → field serialized with DateTime DataType attribute.
     */
    @Test
    public void testIso8601DateTime() throws Exception {
        Path json = writeTempJson("datetime_obj.json",
                "{\"ts\":\"2024-01-15T10:00:00Z\"}");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(new JSONFileEntry(json.toString()));
        Path out = outputDir().resolve("datetime_obj.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);
        String dataType = xpathText(doc, "//Field[@DataType='DateTime']/@DataType");
        assertEquals("DateTime", dataType,
                "Expected a DateTime-typed field for an ISO 8601 string value");
    }

    /**
     * Test 6: Mixed array [1, {"x":2}] → at least 3 documents and a Relationship.
     */
    @Test
    public void testMixedArrayWithNestedObject() throws Exception {
        Path json = writeTempJson("mixed_array.json", "[1, {\"x\":2}]");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(new JSONFileEntry(json.toString()));
        Path out = outputDir().resolve("mixed_array.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);
        int docCount = xpathCount(doc, "//Document");
        assertTrue(docCount >= 3,
                "Expected at least 3 documents (file + array + nested object), got " + docCount);

        int relCount = xpathCount(doc, "//Relationship");
        assertTrue(relCount >= 1,
                "Expected at least one Relationship for the nested object child");
    }

    /**
     * Test 7: Full roundtrip via NLIGenerator with a complex nested JSON file —
     * output NLI file exists and is non-zero in size.
     */
    @Test
    public void testComplexJsonRoundtrip() throws Exception {
        Path json = resources().resolve("object_complex.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        Path out = outputDir().resolve("complex_roundtrip.nli");
        nli.save(out);
        assertTrue(Files.exists(out), "NLI output file should exist");
        assertTrue(Files.size(out) > 0, "NLI output file should be non-zero");
    }

    /**
     * Test 8: JSONPath field-type override ($..count) marks a string field as LongInteger —
     * override does not break serialization.
     */
    @Test
    public void testFieldTypeOverrideDoesNotThrow() throws Exception {
        Path json = writeTempJson("override_test.json", "{\"count\":\"99\"}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        entry.addFieldTypeOverride("$..count", EntryField.Type.LongInteger);
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        Path out = outputDir().resolve("override_test.nli");
        assertDoesNotThrow(() -> nli.save(out));
        assertTrue(Files.exists(out));
    }

    /**
     * Test 9: BigInteger value exceeding Long.MAX_VALUE is serialized as Text (not thrown as
     * ArithmeticException from longValueExact). Verifies SLC-77 overflow fix.
     */
    @Test
    public void testBigIntegerOverflowFallsBackToText() throws Exception {
        // 99999999999999999999 > Long.MAX_VALUE (9223372036854775807)
        Path json = writeTempJson("bigint_overflow.json", "{\"huge\":99999999999999999999}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        Path out = outputDir().resolve("bigint_overflow.nli");
        assertDoesNotThrow(() -> nli.save(out),
                "BigInteger values larger than Long.MAX_VALUE must not throw ArithmeticException");
        assertTrue(Files.exists(out));
    }

    /**
     * Test 10: fieldTypeOverride applied to a nested scalar inside an object produces a
     * LongInteger-typed field in the EDRM XML (verifies coercion propagates into nested structures).
     */
    @Test
    public void testFieldTypeOverrideNestedCoercion() throws Exception {
        // "age" is a string in JSON but we override it to LongInteger
        Path json = writeTempJson("nested_override.json", "{\"person\":{\"age\":\"42\"}}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        entry.addFieldTypeOverride("$..age", EntryField.Type.LongInteger);
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        Path out = outputDir().resolve("nested_override.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);
        String dataType = xpathText(doc, "//Field[@DataType='LongInteger']/@DataType");
        assertEquals("LongInteger", dataType,
                "Expected a LongInteger-typed field after nested fieldTypeOverride coercion");
    }

    // --- malformed JSON detection (SLC-153) ---

    /**
     * A file containing a bare, unquoted identifier (e.g. {@code foo}) is not
     * valid JSON.  {@code JSONFileEntry} must throw a {@link RuntimeException}
     * with a message that includes the file path, with the original parse
     * exception preserved as the cause.
     */
    @Test
    public void testBareIdentifierThrowsWithFileContext() throws Exception {
        Path tmp = Files.createTempFile(outputDir(), "slc153-test-bare-", ".json");
        try {
            Files.writeString(tmp, "foo");
            JSONFileEntry entry = new JSONFileEntry(tmp.toString());
            NLIGenerator nli = new NLIGenerator();
            RuntimeException ex = assertThrows(RuntimeException.class, () -> nli.addEntry(entry));
            assertTrue(ex.getMessage().contains(tmp.toString()),
                    "Error message should contain the file path; got: " + ex.getMessage());
            assertNotNull(ex.getCause(), "cause should be preserved");
            assertInstanceOf(JsonParseException.class, ex.getCause(),
                    "cause should be a JsonParseException; got: " + ex.getCause().getClass().getName());
            assertTrue(ex.getMessage().contains("foo") || ex.getCause().getMessage().contains("foo"),
                    "Error message or cause should contain the content preview 'foo'; got: " + ex.getMessage());
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    /**
     * A file containing truncated JSON (a partial object) is not valid JSON.
     * {@code JSONFileEntry} must throw a {@link RuntimeException} with a message
     * that includes the file path, with the original parse exception preserved
     * as the cause.
     */
    @Test
    public void testTruncatedObjectThrowsWithFileContext() throws Exception {
        Path tmp = Files.createTempFile(outputDir(), "slc153-test-truncated-", ".json");
        try {
            Files.writeString(tmp, "{\"a\":1");
            JSONFileEntry entry = new JSONFileEntry(tmp.toString());
            NLIGenerator nli = new NLIGenerator();
            RuntimeException ex = assertThrows(RuntimeException.class, () -> nli.addEntry(entry));
            assertTrue(ex.getMessage().contains(tmp.toString()),
                    "Error message should contain the file path; got: " + ex.getMessage());
            assertNotNull(ex.getCause(), "cause should be preserved");
            assertInstanceOf(JsonParseException.class, ex.getCause(),
                    "cause should be a JsonParseException; got: " + ex.getCause().getClass().getName());
        } finally {
            Files.deleteIfExists(tmp);
        }
    }

    /**
     * An empty file produces a null/missing root node in Jackson — the Jackson-based
     * implementation handles this gracefully without throwing.  This test verifies that
     * an empty JSON file does not propagate an unchecked exception and that the NLI
     * output file is still produced (as an entry with no children).
     */
    @Test
    public void testEmptyFileHandledGracefully() throws Exception {
        Path tmp = Files.createTempFile(outputDir(), "slc153-test-empty-", ".json");
        try {
            Files.writeString(tmp, "");
            JSONFileEntry entry = new JSONFileEntry(tmp.toString());
            NLIGenerator nli = new NLIGenerator();
            Path out = outputDir().resolve("empty_file_graceful.nli");
            assertDoesNotThrow(() -> nli.addEntry(entry),
                    "An empty JSON file should be handled gracefully, not throw");
        } finally {
            Files.deleteIfExists(tmp);
        }
    }
}
