package com.nuix.nli;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.EntryInterface;
import com.nuix.edrm.datatypes.JSONFileEntry;
import com.nuix.edrm.datatypes.JSONObjectEntry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
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

    // -------------------------------------------------------------------------
    // Missing tests from SLC-65 acceptance criteria (SLC-80)
    // -------------------------------------------------------------------------

    /**
     * testNullValue: A JSON file whose entire content is the literal {@code null}.
     *
     * <p>The null-check in {@link JSONFileEntry#addToBuilder} returns early without creating
     * children, so the family map entry for the file's ID should have zero children.
     * No NPE or exception of any kind should be thrown during parsing or field population.
     */
    @Test
    public void testNullValue(@TempDir Path tempDir) throws Exception {
        Path tempJson = tempDir.resolve("null_value.json");
        Files.writeString(tempJson, "null", StandardCharsets.UTF_8);

        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(tempJson.toString());
        String fileId = fileEntry.addToBuilder(builder);

        // A JSON null root should produce no children: addToBuilder returns immediately after
        // registering the file entry itself.
        Map<String, List<String>> familyMap = builder.getFamilyMap();
        List<String> children = familyMap.getOrDefault(fileId, List.of());
        assertTrue(children.isEmpty(),
                "A JSON null root should produce no child entries; found: " + children);
    }

    /**
     * testCustomRootFactory: Subclass {@link JSONFileEntry} via the generator-class constructor
     * to inject a custom {@link JSONObjectEntry} subclass ({@link TaggedObjectEntry}) as the root.
     *
     * <p>Asserts that the builder's entry map contains an instance of the custom subclass,
     * confirming that the objectClass parameter is honoured by the factory.
     */
    @Test
    public void testCustomRootFactory() {
        // Use the generator-class constructor so the factory produces TaggedObjectEntry instances.
        JSONFileEntry customEntry = new JSONFileEntry(
                resources().resolve("object_mixed.json").toString(),
                "application/json",
                null,
                null,        // valueClass — use default
                null,        // arrayClass — use default
                TaggedObjectEntry.class);

        EDRMBuilder builder = new EDRMBuilder();
        String fileId = customEntry.addToBuilder(builder);

        // The builder must contain at least one TaggedObjectEntry as a direct child of the file.
        Map<String, List<String>> familyMap = builder.getFamilyMap();
        List<String> children = familyMap.getOrDefault(fileId, List.of());
        assertFalse(children.isEmpty(),
                "object_mixed.json should produce at least one child entry");

        boolean foundTagged = children.stream()
                .map(id -> builder.getEntry(id))
                .anyMatch(e -> e instanceof TaggedObjectEntry);
        assertTrue(foundTagged,
                "At least one direct child of the JSONFileEntry should be a TaggedObjectEntry");
    }

    /**
     * testDeepNesting: A 3-level parent chain is fully expressed in the EDRM
     * {@code <Relationship>} elements.
     *
     * <p>The chain is:
     * <pre>
     *   Level 1: root MappingEntry   (added via builder.addMapping)
     *   Level 2: JSONFileEntry        (simple_str.json, parented to L1)
     *   Level 3: JSONValueEntry       (scalar child auto-created by JSONFileEntry.addToBuilder)
     * </pre>
     * Using {@code addMapping} for the root gives it a distinct SHA-1 identity from the JSON
     * file, avoiding the identity collision that occurs when two FileEntry objects point to the
     * same path.  The test verifies both links of the chain (L1→L2 and L2→L3) are present as
     * separate {@code <Relationship>} elements and asserts exactly 2 relationships total.
     */
    @Test
    public void testDeepNesting() {
        EDRMBuilder builder = new EDRMBuilder();

        // Level 1: root mapping entry (distinct identity from the JSON file below)
        String rootId = builder.addMapping(
                Map.of("description", "root container for deep-nesting test"),
                "application/x-test-root");

        // Level 2: JSONFileEntry for simple_str.json, parented to the root mapping
        Path jsonPath = resources().resolve("simple_str.json");
        JSONFileEntry fileEntry = new JSONFileEntry(jsonPath.toString(), "application/json", rootId);
        String fileId = fileEntry.addToBuilder(builder);

        // Level 3: JSONValueEntry is auto-created by addToBuilder as a child of fileId.
        Map<String, List<String>> familyMap = builder.getFamilyMap();
        List<String> fileChildren = familyMap.getOrDefault(fileId, List.of());
        assertEquals(1, fileChildren.size(),
                "simple_str.json has a scalar root, so it should produce exactly one child");
        String valueId = fileChildren.get(0);

        // Build EDRM XML and inspect the <Relationships> section.
        Document doc = builder.build();
        NodeList relationships = doc.getElementsByTagName("Relationship");
        assertEquals(2, relationships.getLength(),
                "A 3-level chain (root→file→value) requires exactly 2 <Relationship> elements");

        boolean foundRootToFile  = false;
        boolean foundFileToValue = false;
        for (int i = 0; i < relationships.getLength(); i++) {
            Element rel = (Element) relationships.item(i);
            String parent = rel.getAttribute("ParentDocId");
            String child  = rel.getAttribute("ChildDocId");
            if (rootId.equals(parent) && fileId.equals(child))  foundRootToFile  = true;
            if (fileId.equals(parent) && valueId.equals(child)) foundFileToValue = true;
        }
        assertTrue(foundRootToFile,
                "Missing Relationship: root MappingEntry (L1) → JSONFileEntry (L2)");
        assertTrue(foundFileToValue,
                "Missing Relationship: JSONFileEntry (L2) → JSONValueEntry (L3)");
    }

    // -------------------------------------------------------------------------
    // Static nested helper classes
    // -------------------------------------------------------------------------

    /**
     * Custom JSONObjectEntry subclass used by testCustomRootFactory to verify that the
     * generator-class constructor of JSONFileEntry is honoured.
     *
     * <p>Must be {@code static} and package-accessible so that {@link JsonEntryFactory} can
     * reflectively instantiate it via the 4-arg constructor.
     */
    static class TaggedObjectEntry extends JSONObjectEntry {
        TaggedObjectEntry(String mappingName, Map<String, Object> object, String mimeType, String parentId) {
            super(mappingName, object, mimeType, parentId);
        }
    }
}
