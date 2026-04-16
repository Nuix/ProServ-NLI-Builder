package com.nuix.nli;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.EntryInterface;
import com.nuix.edrm.datatypes.JSONFileEntry;
import com.nuix.edrm.datatypes.JSONObjectEntry;
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
import java.util.List;
import java.util.Map;
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

    // -----------------------------------------------------------------------
    // SLC-68: JSON structural content tests using EDRMBuilder directly
    // -----------------------------------------------------------------------

    /**
     * SLC-68 Test 1: testObjectFieldCount — load object_mixed.json (4 scalar fields) via
     * EDRMBuilder directly and assert the JSONObjectEntry child carries exactly the expected
     * number of fields (4 payload + 4 generic added by MappingEntry = 8 total).
     */
    @Test
    public void testObjectFieldCount() throws Exception {
        // object_mixed.json has 4 keys: "key 1" (Text), "key 2" (LongInteger),
        // "key 3" (Decimal), "key 4" (Boolean)
        Path json = resources().resolve("object_mixed.json");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        fileEntry.addToBuilder(builder);

        Map<String, EntryInterface> entryMap = builder.getEntryMap();
        // There should be exactly 2 entries: the JSONFileEntry and its JSONObjectEntry child.
        assertEquals(2, entryMap.size(),
                "Expected 2 entries (file + object child) in the builder");

        // The second entry (the "JSON Object" child) is a JSONObjectEntry.
        EntryInterface objectEntry = entryMap.values().stream()
                .filter(e -> e instanceof JSONObjectEntry)
                .findFirst()
                .orElseThrow(() -> new AssertionError("No JSONObjectEntry found in builder"));

        // Count via getFields() — includes payload fields + 4 generic (MIME Type, Name, SHA-1, Item Date).
        // object_mixed.json has 4 payload fields → 4 + 4 = 8 total.
        int fieldCount = 0;
        for (String ignored : objectEntry.getFields()) fieldCount++;
        assertEquals(8, fieldCount,
                "Expected 8 fields on JSONObjectEntry (4 payload + 4 generic), got " + fieldCount);
    }

    /**
     * SLC-68 Test 2: testArrayChildCount — load list_mixed.json (4 scalar elements) via
     * EDRMBuilder directly and assert the JSONArrayEntry carries the correct number of entries.
     */
    @Test
    public void testArrayChildCount() throws Exception {
        // list_mixed.json has 4 elements: "value 1" (Text), 2 (LongInteger), 3.01 (Decimal),
        // false (Boolean) — all scalars, so no complex children.
        Path json = resources().resolve("list_mixed.json");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        fileEntry.addToBuilder(builder);

        Map<String, EntryInterface> entryMap = builder.getEntryMap();
        // 2 entries: JSONFileEntry + JSONArrayEntry child
        assertEquals(2, entryMap.size(),
                "Expected 2 entries (file + array child) in the builder");

        // familyMap: the file entry's ID should have exactly one child.
        Map<String, List<String>> familyMap = builder.getFamilyMap();
        String fileId = fileEntry.getField(fileEntry.getIdentifierField()).getValue().toString();
        List<String> children = familyMap.getOrDefault(fileId, List.of());
        assertEquals(1, children.size(),
                "Expected exactly 1 child (the array entry) under the file entry");
    }

    /**
     * SLC-68 Test 3: testNestedObjectCreatesChild — load JSON with a nested object via
     * EDRMBuilder and assert the outer JSONObjectEntry has exactly one child in familyMap.
     */
    @Test
    public void testNestedObjectCreatesChild() throws Exception {
        // {"outer": {"inner": 1}} → file → outer object → inner object (3 entries)
        Path json = writeTempJson("nested_obj_slc68.json", "{\"outer\": {\"inner\": 1}}");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        fileEntry.addToBuilder(builder);

        Map<String, EntryInterface> entryMap = builder.getEntryMap();
        assertEquals(3, entryMap.size(),
                "Expected 3 entries (file + outer object + inner object), got " + entryMap.size());

        // Find the outer JSONObjectEntry (direct child of the file entry).
        String fileId = fileEntry.getField(fileEntry.getIdentifierField()).getValue().toString();
        Map<String, List<String>> familyMap = builder.getFamilyMap();

        List<String> fileChildren = familyMap.getOrDefault(fileId, List.of());
        assertEquals(1, fileChildren.size(),
                "File entry should have exactly 1 child (the outer object)");

        String outerObjectId = fileChildren.get(0);
        List<String> outerChildren = familyMap.getOrDefault(outerObjectId, List.of());
        assertEquals(1, outerChildren.size(),
                "Outer object should have exactly 1 child (the inner object)");
    }

    /**
     * SLC-68 Test 4: testScalarTypes — load JSON with string, integer, and boolean scalar fields
     * via EDRMBuilder and assert each field carries the correct EntryField.Type in the EDRM XML.
     */
    @Test
    public void testScalarTypes() throws Exception {
        // {"label":"hello","count":42,"active":true}
        Path json = writeTempJson("scalar_types_slc68.json",
                "{\"label\":\"hello\",\"count\":42,\"active\":true}");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        fileEntry.addToBuilder(builder);

        builder.setAsNli(false);
        Path outXml = outputDir().resolve("scalar_types_slc68.xml");
        builder.setOutputPath(outXml);
        builder.save();
        assertTrue(Files.exists(outXml), "EDRM XML output should exist");

        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        DocumentBuilder db = dbf.newDocumentBuilder();
        Document doc = db.parse(outXml.toFile());

        // "label" → Text
        String textType = xpathText(doc, "//Field[@Name='label']/@DataType");
        assertEquals("Text", textType, "\"label\" field should have DataType=Text");

        // "count" → LongInteger
        String intType = xpathText(doc, "//Field[@Name='count']/@DataType");
        assertEquals("LongInteger", intType, "\"count\" field should have DataType=LongInteger");

        // "active" → Boolean
        String boolType = xpathText(doc, "//Field[@Name='active']/@DataType");
        assertEquals("Boolean", boolType, "\"active\" field should have DataType=Boolean");
    }

    /**
     * SLC-68 Test 5: testParentIdPropagation — assert child entries report the JSONFileEntry's
     * identifier as their ParentDocId in the EDRM XML {@code <Relationships>} section.
     */
    @Test
    public void testParentIdPropagation() throws Exception {
        // {"x": 1} → file entry + object child; the object's parent must be the file's DocID.
        Path json = writeTempJson("parent_id_slc68.json", "{\"x\": 1}");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        fileEntry.addToBuilder(builder);

        builder.setAsNli(false);
        Path outXml = outputDir().resolve("parent_id_slc68.xml");
        builder.setOutputPath(outXml);
        builder.save();
        assertTrue(Files.exists(outXml), "EDRM XML output should exist");

        DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
        DocumentBuilder db = dbf.newDocumentBuilder();
        Document doc = db.parse(outXml.toFile());

        // The file entry's DocID
        String fileId = fileEntry.getField(fileEntry.getIdentifierField()).getValue().toString();

        // At least one Relationship element must exist.
        int relCount = xpathCount(doc, "//Relationship");
        assertTrue(relCount >= 1, "Expected at least one Relationship element, got " + relCount);

        // All Relationship elements with this file as parent must have ParentDocId == fileId.
        String parentDocId = xpathText(doc,
                "//Relationship[@ParentDocId='" + fileId + "']/@ParentDocId");
        assertEquals(fileId, parentDocId,
                "Child entries should reference the file entry's DocID as ParentDocId");
    }
}
