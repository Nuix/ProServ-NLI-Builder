package com.nuix.nli;

import com.fasterxml.jackson.core.JsonParseException;
import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.EntryInterface;
import com.nuix.edrm.datatypes.JSONFileEntry;
import com.nuix.edrm.datatypes.JSONObjectEntry;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.api.parallel.Execution;
import org.junit.jupiter.api.parallel.ExecutionMode;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
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

// The @BeforeEach deletes all .nli files from outputDir() before each test. This is safe
// for serial execution but would cause intermittent failures under JUnit 5 parallel
// execution (concurrent tests would delete each other's in-flight output). This annotation
// ensures the class always runs single-threaded regardless of project-level parallelism config.
@Execution(ExecutionMode.SAME_THREAD)
public class JsonTests {
    private Path resources() { return Paths.get(".", "src", "test", "resources").toAbsolutePath().normalize(); }
    private Path outputDir() { return Paths.get("build", "test-output", "json").toAbsolutePath().normalize(); }

    @BeforeEach
    void ensureOutputDir() throws Exception {
        Files.createDirectories(outputDir());
        // Delete stale .nli output files so that assertTrue(Files.exists(out)) cannot
        // pass trivially from a previous test run — the file must be freshly produced.
        try (var stream = Files.list(outputDir())) {
            stream.filter(p -> p.toString().endsWith(".nli"))
                  .forEach(p -> {
                      try { Files.deleteIfExists(p); }
                      catch (java.io.IOException ignored) { }
                  });
        }
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
    // Resource-file roundtrip tests (parameterized, SLC-174)
    // -----------------------------------------------------------------------

    /**
     * Parameterized roundtrip: load a JSON resource file, write an NLI, verify the NLI exists and
     * contains at least {@code minDocCount} EDRM {@code <Document>} elements.
     *
     * <p>Row format: {@code resourceName, outputName, minDocCount}
     * <ul>
     *   <li>{@code simple_str.json} — scalar string root; file entry + value child = ≥ 2 documents
     *   <li>{@code object_complex.json} — deeply nested object; traversal must descend into nested
     *       structures, so ≥ 10 documents confirms recursive traversal is working
     * </ul>
     */
    @ParameterizedTest(name = "{0} -> {1} (minDocs={2})")
    @CsvSource({
        "simple_str.json,     simple_str.nli,       2",
        "object_complex.json, complex_roundtrip.nli, 10"
    })
    public void testResourceFileRoundtrip(String resourceName, String outputName, int minDocCount) throws Exception {
        Path json = resources().resolve(resourceName);
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        Path out = outputDir().resolve(outputName);
        nli.save(out);
        assertTrue(Files.exists(out), "NLI output file should exist: " + out);
        assertTrue(Files.size(out) > 0, "NLI output file should be non-zero: " + out);

        Document doc = getEdrmXmlFromNli(out);
        int docCount = xpathCount(doc, "//Document");
        assertTrue(docCount >= minDocCount,
                "Expected at least " + minDocCount + " documents in NLI for " + resourceName + ", got " + docCount);
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

    // --- malformed JSONPath pattern validation (SLC-256) and null type guard (SLC-259) ---

    /**
     * SLC-256: A pattern of the form {@code $..foo.bar} (recursive-descent with a dotted key)
     * must be rejected by {@link JSONFileEntry#addFieldTypeOverride} with an
     * {@link IllegalArgumentException}.
     *
     * <p>Without the guard, the key extracted by {@code pattern.substring(3)} is {@code "foo.bar"},
     * which can never match any real JSON field name; the override silently does nothing.
     */
    @Test
    public void testMalformedJsonPathRecursiveDescentNestedKeyThrows() {
        JSONFileEntry entry = new JSONFileEntry("/dev/null");
        assertThrows(IllegalArgumentException.class,
                () -> entry.addFieldTypeOverride("$..foo.bar", EntryField.Type.LongInteger),
                "addFieldTypeOverride must reject '$..foo.bar' — dotted keys after '$..'" +
                " can never match a real field name and would register a silent no-op");
    }

    /**
     * SLC-259: Passing {@code null} as the {@code type} parameter to
     * {@link JSONFileEntry#addFieldTypeOverride} must throw {@link IllegalArgumentException}.
     *
     * <p>Without the null-check, a null type is silently stored and
     * {@code resolveTypeOverride} returns null, which is indistinguishable from
     * "no override registered" — a silent no-op.
     */
    @Test
    public void testNullTypeInAddFieldTypeOverrideThrows() {
        JSONFileEntry entry = new JSONFileEntry("/dev/null");
        assertThrows(IllegalArgumentException.class,
                () -> entry.addFieldTypeOverride("$..key", null),
                "addFieldTypeOverride must reject a null type parameter");
    }

    // --- null root JSON (SLC-175) ---

    /**
     * A JSON file whose entire content is the literal {@code null} is valid JSON.
     * Jackson parses it as a NullNode whose {@code isNull()} returns {@code true}.
     * {@code JSONFileEntry.addToBuilder} must handle this by returning early without
     * adding any child entries — the NLI must be produced with exactly one
     * {@code <Document>} element (the file entry itself) and must not throw.
     *
     * <p>This is the only test that exercises the {@code root.isNull()} early-return
     * branch in {@code JSONFileEntry.addToBuilder}.
     */
    @Test
    public void testRootNullProducesFileEntryOnly() throws Exception {
        Path json = writeTempJson("null_root.json", "null");
        NLIGenerator nli = new NLIGenerator();
        assertDoesNotThrow(() -> nli.addEntry(new JSONFileEntry(json.toString())),
                "A root-null JSON document must not throw during addEntry");
        Path out = outputDir().resolve("null_root.nli");
        nli.save(out);
        assertTrue(Files.exists(out), "NLI output file should exist for null-root JSON");

        // The root NullNode triggers an early return; no child entry is added.
        // Exactly one <Document> (the JSONFileEntry itself) must be present.
        Document doc = getEdrmXmlFromNli(out);
        int docCount = xpathCount(doc, "//Document");
        assertEquals(1, docCount,
                "A null-root JSON document should produce exactly 1 Document (the file entry, no children), got " + docCount);
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
     * output file is still produced (as an archive with no JSON child entries).
     */
    @Test
    public void testEmptyFileHandledGracefully() throws Exception {
        Path tmp = Files.createTempFile(outputDir(), "slc153-test-empty-", ".json");
        Path out = outputDir().resolve("empty_file_graceful.nli");
        try {
            Files.writeString(tmp, "");
            JSONFileEntry entry = new JSONFileEntry(tmp.toString());
            NLIGenerator nli = new NLIGenerator();
            assertDoesNotThrow(() -> nli.addEntry(entry),
                    "An empty JSON file should be handled gracefully, not throw");
            nli.save(out);
            assertTrue(Files.exists(out), "NLI output file should exist even for empty JSON input");
        } finally {
            Files.deleteIfExists(tmp);
            Files.deleteIfExists(out);
        }
    }

    // -----------------------------------------------------------------------
    // SLC-241: Custom root factory — TaggedObjectEntry subclass
    // -----------------------------------------------------------------------

    /**
     * Minimal {@link JSONObjectEntry} subclass used by {@link #testCustomRootFactory} to verify
     * that {@code JsonEntryFactory.createObject()} can reflectively instantiate a custom subclass.
     *
     * <p>The constructor must be {@code public} because {@code JsonEntryFactory.createObject()}
     * uses {@link Class#getConstructor(Class[])} which only finds public constructors.
     */
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

    // -----------------------------------------------------------------------
    // SLC-241: Custom root factory — TaggedObjectEntry subclass
    // -----------------------------------------------------------------------

    /**
     * Minimal {@link JSONObjectEntry} subclass used by {@link #testCustomRootFactory} to verify
     * that {@code JsonEntryFactory.createObject()} can reflectively instantiate a custom subclass.
     *
     * <p>The constructor must be {@code public} because {@code JsonEntryFactory.createObject()}
     * uses {@link Class#getConstructor(Class[])} which only finds public constructors.
     */
    public static class TaggedObjectEntry extends JSONObjectEntry {
        public TaggedObjectEntry(String mappingName, Map<String, Object> object,
                                 String mimeType, String parentId) {
            super(mappingName, object, mimeType, parentId);
        }
    }

    /**
     * SLC-241 + SLC-243: Verify that {@code JsonEntryFactory.createObject()} can reflectively
     * instantiate {@link TaggedObjectEntry} and that the resulting entry is correctly initialized
     * — i.e. that field values from the JSON content are present in the EDRM XML output.
     *
     * <p>If the constructor were package-private the factory would throw a
     * {@link NoSuchMethodException} wrapped in a {@link RuntimeException}.
     */
    @Test
    public void testCustomRootFactory() throws Exception {
        // JSON has two scalar fields: "label" (Text) and "count" (LongInteger)
        Path json = writeTempJson("custom_root_factory.json", "{\"label\":\"hello\",\"count\":7}");
        JSONFileEntry entry = new JSONFileEntry(
                json.toString(),
                "application/json",
                null,
                null,
                null,
                TaggedObjectEntry.class
        );

        NLIGenerator nli = new NLIGenerator();
        // The factory must not throw; if the constructor is package-private this line fails.
        assertDoesNotThrow(() -> nli.addEntry(entry),
                "JsonEntryFactory.createObject() must reflectively instantiate TaggedObjectEntry without throwing");

        Path out = outputDir().resolve("custom_root_factory.nli");
        nli.save(out);
        assertTrue(Files.exists(out), "NLI output file should exist: " + out);

        Document doc = getEdrmXmlFromNli(out);

        // Verify the custom entry contributed at least a root + the two scalar children
        int docCount = xpathCount(doc, "//Document");
        assertTrue(docCount >= 2,
                "Expected at least 2 Documents (file entry + custom root object), got " + docCount);

        // SLC-243: Verify field values from the JSON content appear in the EDRM output,
        // confirming the custom TaggedObjectEntry is correctly initialized, not just instantiated.
        String labelValue = xpathText(doc, "//FieldValues/*[parent::FieldValues and contains(text(),'hello')]");
        assertFalse(labelValue.isEmpty(),
                "Expected the 'label' field value 'hello' to appear in a FieldValues element");

        String countValue = xpathText(doc, "//FieldValues/*[parent::FieldValues and text()='7']");
        assertFalse(countValue.isEmpty(),
                "Expected the 'count' field value '7' to appear in a FieldValues element");
    }

    // SLC-82: Malformed JSONPath handling in parseJsonPathSegments
    // -----------------------------------------------------------------------

    /**
     * Test 11: A pattern ending with a trailing dot must throw IllegalArgumentException.
     * Previously, rest.split("\\.") would silently drop the trailing empty segment,
     * producing wrong match results instead of a clear error.
     */
    @Test
    public void testMalformedJsonPathTrailingDotThrows() throws Exception {
        Path json = writeTempJson("malformed_trailing_dot.json", "{\"foo\":1}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        assertThrows(IllegalArgumentException.class,
                () -> entry.addFieldTypeOverride("$.foo.", EntryField.Type.LongInteger),
                "A trailing dot in a JSONPath pattern must throw IllegalArgumentException");
    }

    /**
     * Test 12: A pattern with consecutive dots (e.g. $.foo..bar used as a direct path,
     * not as a recursive-descent $.. prefix) must throw IllegalArgumentException.
     */
    @Test
    public void testMalformedJsonPathConsecutiveDotsThrows() throws Exception {
        Path json = writeTempJson("malformed_consecutive_dots.json", "{\"foo\":{\"bar\":1}}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        // $.foo..bar is not the same as $..bar — it is a malformed direct path
        assertThrows(IllegalArgumentException.class,
                () -> entry.addFieldTypeOverride("$.foo..bar", EntryField.Type.LongInteger),
                "Consecutive dots in a direct JSONPath pattern must throw IllegalArgumentException");
    }

    /**
     * Test 13: A pattern with no '$' prefix must throw IllegalArgumentException.
     */
    @Test
    public void testMalformedJsonPathNoPrefixThrows() throws Exception {
        Path json = writeTempJson("malformed_no_prefix.json", "{\"foo\":1}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        assertThrows(IllegalArgumentException.class,
                () -> entry.addFieldTypeOverride("foo.bar", EntryField.Type.LongInteger),
                "A JSONPath pattern without a '$' prefix must throw IllegalArgumentException");
    }

    /**
     * Test 14: A recursive-descent pattern with no key after '$..'' must throw
     * IllegalArgumentException to prevent matching every leaf node.
     */
    @Test
    public void testMalformedJsonPathRecursiveDescentNoKeyThrows() throws Exception {
        Path json = writeTempJson("malformed_recursive_nokey.json", "{\"foo\":1}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        assertThrows(IllegalArgumentException.class,
                () -> entry.addFieldTypeOverride("$..", EntryField.Type.LongInteger),
                "'$..' with no key must throw IllegalArgumentException");
    }

    /**
     * Test 15: A null pattern must throw IllegalArgumentException.
     */
    @Test
    public void testMalformedJsonPathNullThrows() throws Exception {
        Path json = writeTempJson("malformed_null.json", "{\"foo\":1}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        assertThrows(IllegalArgumentException.class,
                () -> entry.addFieldTypeOverride(null, EntryField.Type.LongInteger),
                "A null JSONPath pattern must throw IllegalArgumentException");
    }

    /**
     * Test 16: Valid patterns must still register without error after the validation
     * fix (regression guard).
     */
    @Test
    public void testValidJsonPathPatternsDoNotThrow() throws Exception {
        Path json = writeTempJson("valid_patterns.json", "{\"a\":{\"b\":1}}");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        assertDoesNotThrow(() -> {
            entry.addFieldTypeOverride("$..b",         EntryField.Type.LongInteger);
            entry.addFieldTypeOverride("$.a",           EntryField.Type.Text);
            entry.addFieldTypeOverride("$.a.b",         EntryField.Type.LongInteger);
            entry.addFieldTypeOverride("$.arr[*].key",  EntryField.Type.Text);
        }, "Valid JSONPath patterns must not throw during registration");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        Path out = outputDir().resolve("valid_patterns.nli");
        assertDoesNotThrow(() -> nli.save(out),
                "Saving with valid JSONPath patterns must not throw");
        assertTrue(Files.exists(out));
    }

    // SLC-153: Malformed JSON file content detection
    // -----------------------------------------------------------------------

    /**
     * Test 17: A JSON file containing garbage (non-JSON text) must throw a RuntimeException
     * when addToBuilder is called. The exception is caused by Jackson being unable to parse
     * the content as valid JSON.
     */
    @Test
    public void testMalformedJsonFileGarbageThrows() throws Exception {
        Path json = writeTempJson("garbage_content.json", "this is not json at all");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        assertThrows(RuntimeException.class,
                () -> nli.addEntry(entry),
                "A file containing non-JSON garbage content must throw RuntimeException during addToBuilder");
    }

    /**
     * Test 18: A JSON file with truncated/incomplete content must throw a RuntimeException
     * when addToBuilder is called. The exception is caused by Jackson detecting the unexpected
     * end of input while parsing.
     */
    @Test
    public void testMalformedJsonFileTruncatedThrows() throws Exception {
        Path json = writeTempJson("truncated_content.json", "{\"a\":1");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        assertThrows(RuntimeException.class,
                () -> nli.addEntry(entry),
                "A truncated JSON file must throw RuntimeException during addToBuilder");
    }

    /**
     * Test 19: The RuntimeException thrown for a malformed JSON file must include the file path
     * in its message, enabling fast diagnosis of which file caused the parse failure.
     * This is the key diagnostic contract introduced by SLC-153.
     */
    @Test
    public void testMalformedJsonFileErrorMessageContainsFilePath() throws Exception {
        Path json = writeTempJson("malformed_for_path_check.json", "not valid json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        RuntimeException ex = assertThrows(RuntimeException.class,
                () -> nli.addEntry(entry),
                "Parsing a malformed JSON file must throw RuntimeException");
        String msg = ex.getMessage() == null ? "" : ex.getMessage();
        assertTrue(msg.contains(json.toString()) || msg.contains(json.getFileName().toString()),
                "The RuntimeException message must contain the file path for diagnostics, but was: " + msg);
    }

    // -------------------------------------------------------------------------
    // SLC-172: Regression tests — string roots that look like other types (SLC-149 fix guard)
    // -------------------------------------------------------------------------

    /**
     * Regression test for SLC-149: a JSON string whose value begins with {@code [} must be
     * classified as a scalar value ({@code application/x-json-value}), not as an array.
     *
     * <p>The old {@code startsWith} heuristic in the pre-Jackson implementation would have
     * misidentified this as an array root, producing a child with the wrong MIME type. This
     * test parses the generated NLI and asserts the child entry's {@code MimeType} attribute
     * so that any regression in root-type detection immediately fails here rather than
     * silently producing a wrong output file.
     */
    @Test
    public void testStringRootLooksLikeArray() throws Exception {
        // A JSON string value that starts with '[' — must be treated as a scalar, not an array.
        Path json = writeTempJson("string_looks_like_array.json", "\"[not an array]\"");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(new JSONFileEntry(json.toString()));
        Path out = outputDir().resolve("string_looks_like_array.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);

        // The child Document element must have MimeType="application/x-json-value", NOT
        // "application/x-json-array". A regression in Jackson root-type detection would
        // produce the wrong MIME type and this assertion would catch it.
        String mimeType = xpathText(doc,
                "//Document[@MimeType='application/x-json-value']/@MimeType");
        assertEquals("application/x-json-value", mimeType,
                "A string root starting with '[' must produce a JSONValueEntry "
                + "(application/x-json-value), not a JSONArrayEntry");

        // Also verify that the array MIME type is NOT present — belt-and-suspenders.
        String arrayMime = xpathText(doc,
                "//Document[@MimeType='application/x-json-array']/@MimeType");
        assertTrue(arrayMime.isEmpty(),
                "No application/x-json-array entry should exist for a string root");
    }

    /**
     * Regression test for SLC-149: a JSON string whose value begins with {@code {}} must be
     * classified as a scalar value ({@code application/x-json-value}), not as an object.
     *
     * <p>Mirrors {@link #testStringRootLooksLikeArray} for the object-lookalike case.
     */
    @Test
    public void testStringRootLooksLikeObject() throws Exception {
        // A JSON string value that starts with '{' — must be treated as a scalar, not an object.
        Path json = writeTempJson("string_looks_like_object.json", "\"{not an object}\"");
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(new JSONFileEntry(json.toString()));
        Path out = outputDir().resolve("string_looks_like_object.nli");
        nli.save(out);
        assertTrue(Files.exists(out));

        Document doc = getEdrmXmlFromNli(out);

        // The child Document element must have MimeType="application/x-json-value", NOT
        // "application/x-json-object".
        String mimeType = xpathText(doc,
                "//Document[@MimeType='application/x-json-value']/@MimeType");
        assertEquals("application/x-json-value", mimeType,
                "A string root starting with '{' must produce a JSONValueEntry "
                + "(application/x-json-value), not a JSONObjectEntry");

        // Also verify that the object MIME type is NOT present.
        String objectMime = xpathText(doc,
                "//Document[@MimeType='application/x-json-object']/@MimeType");
        assertTrue(objectMime.isEmpty(),
                "No application/x-json-object entry should exist for a string root");
    }

    // -------------------------------------------------------------------------
    // SLC-150: JSON string escape sequence decoding (regression guard)
    // -------------------------------------------------------------------------

    /**
     * testScalarStringNewlineEscape: A root JSON string containing a {@code \n} escape
     * sequence must be decoded to an actual newline character, not the two-character literal
     * {@code \n}.
     *
     * <p>A naive {@code content.substring(1, content.length() - 1)} implementation strips
     * the surrounding quotes but leaves JSON escape sequences unprocessed. The correct
     * implementation delegates to the JSON parser (Jackson's {@code node.textValue()}) which
     * always returns the decoded Java string.
     */
    @Test
    public void testScalarStringNewlineEscape(@TempDir Path tempDir) throws Exception {
        // JSON: "hello\nworld" — the \n is a JSON escape, must become a real newline
        Path json = tempDir.resolve("escape_newline.json");
        Files.writeString(json, "\"hello\\nworld\"", StandardCharsets.UTF_8);

        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        fileEntry.addToBuilder(builder);

        // The scalar child should carry the field value "hello\nworld" (real newline).
        Map<String, EntryInterface> entryMap = builder.getEntryMap();
        boolean foundDecodedNewline = entryMap.values().stream()
                .filter(e -> !(e instanceof JSONFileEntry))
                .flatMap(e -> {
                    java.util.stream.Stream.Builder<String> sb = java.util.stream.Stream.builder();
                    for (String fieldName : e.getFields()) {
                        Object val = e.getField(fieldName).getValue();
                        if (val != null) sb.accept(val.toString());
                    }
                    return sb.build();
                })
                .anyMatch(v -> v.contains("\n"));

        assertTrue(foundDecodedNewline,
                "JSON \\n escape in a scalar string must be decoded to a real newline character, " +
                "not the literal two-character sequence '\\\\n'");
    }

    /**
     * testScalarStringUnicodeEscape: A root JSON string containing a {@code \u0041} Unicode
     * escape must be decoded to the character {@code A}, not the literal 6-character sequence
     * {@code \u0041}.
     */
    @Test
    public void testScalarStringUnicodeEscape(@TempDir Path tempDir) throws Exception {
        // JSON: "\u0041" — Unicode escape for the letter 'A'
        Path json = tempDir.resolve("escape_unicode.json");
        Files.writeString(json, "\"\\u0041\"", StandardCharsets.UTF_8);

        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        fileEntry.addToBuilder(builder);

        Map<String, EntryInterface> entryMap = builder.getEntryMap();
        boolean foundDecodedUnicode = entryMap.values().stream()
                .filter(e -> !(e instanceof JSONFileEntry))
                .flatMap(e -> {
                    java.util.stream.Stream.Builder<String> sb = java.util.stream.Stream.builder();
                    for (String fieldName : e.getFields()) {
                        Object val = e.getField(fieldName).getValue();
                        if (val != null) sb.accept(val.toString());
                    }
                    return sb.build();
                })
                .anyMatch(v -> v.equals("A"));

        assertTrue(foundDecodedUnicode,
                "JSON \\u0041 escape in a scalar string must be decoded to 'A', " +
                "not the literal string '\\\\u0041'");
    }

    /**
     * testObjectFieldStringEscapeDecoding: String fields inside a JSON object must also
     * have their escape sequences decoded. A field value {@code "hello\tworld"} must contain
     * a real tab character.
     */
    @Test
    public void testObjectFieldStringEscapeDecoding(@TempDir Path tempDir) throws Exception {
        // JSON object with a tab escape in a field value
        Path json = tempDir.resolve("escape_tab_field.json");
        Files.writeString(json, "{\"msg\":\"hello\\tworld\"}", StandardCharsets.UTF_8);

        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        fileEntry.addToBuilder(builder);

        Map<String, EntryInterface> entryMap = builder.getEntryMap();
        boolean foundDecodedTab = entryMap.values().stream()
                .filter(e -> !(e instanceof JSONFileEntry))
                .flatMap(e -> {
                    java.util.stream.Stream.Builder<String> sb = java.util.stream.Stream.builder();
                    for (String fieldName : e.getFields()) {
                        Object val = e.getField(fieldName).getValue();
                        if (val != null) sb.accept(val.toString());
                    }
                    return sb.build();
                })
                .anyMatch(v -> v.contains("\t"));

        assertTrue(foundDecodedTab,
                "JSON \\t escape in an object field value must be decoded to a real tab character");
    }
}
