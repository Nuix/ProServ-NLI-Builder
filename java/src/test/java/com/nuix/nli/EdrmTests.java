package com.nuix.nli;

import com.nuix.edrm.DirectoryEntry;
import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EDRMUtilities;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.FieldFactory;
import com.nuix.edrm.FileEntry;
import com.nuix.edrm.MappingEntry;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.w3c.dom.Document;
import org.w3c.dom.NodeList;

import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import javax.xml.namespace.QName;
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
import javax.xml.xpath.XPathExpressionException;
import javax.xml.xpath.XPathFactory;
import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

public class EdrmTests {
    // XPathFactory construction performs service-loader discovery on every call.
    // Promote to a shared static instance so all helper invocations reuse it.
    private static final XPathFactory XPATH_FACTORY = XPathFactory.newInstance();

    private Path resources() { return Paths.get(".", "src", "test", "resources").toAbsolutePath().normalize(); }
    private Path outputDir() { return Paths.get("build", "test-output").toAbsolutePath().normalize(); }

    /** Convert a DOM Document to an XML string for easy assertion. */
    private String docToString(Document doc) {
        try {
            Transformer t = TransformerFactory.newInstance().newTransformer();
            t.setOutputProperty(OutputKeys.INDENT, "yes");
            t.setOutputProperty(OutputKeys.METHOD, "xml");
            StringWriter sw = new StringWriter();
            t.transform(new DOMSource(doc), new StreamResult(sw));
            return sw.toString();
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * Shared XPath evaluation delegate. Creates a new XPath instance from the cached factory
     * (XPath instances are not thread-safe, so one per call is correct) and evaluates the
     * expression against the provided document with the specified return type.
     *
     * @param doc        the DOM Document to evaluate against
     * @param expression the XPath expression string
     * @param returnType one of {@link XPathConstants#NODESET}, {@link XPathConstants#STRING}, etc.
     * @return the evaluation result cast to the type implied by {@code returnType}
     */
    private Object evaluate(Document doc, String expression, QName returnType) {
        try {
            XPath xp = XPATH_FACTORY.newXPath();
            return xp.evaluate(expression, doc, returnType);
        } catch (XPathExpressionException e) {
            throw new RuntimeException(e);
        }
    }

    /** Evaluate an XPath expression returning a NodeList against a Document. */
    private NodeList xpath(Document doc, String expression) {
        return (NodeList) evaluate(doc, expression, XPathConstants.NODESET);
    }

    /** Evaluate an XPath expression against a Document and return the string result. */
    private String xpathStr(Document doc, String expression) {
        return (String) evaluate(doc, expression, XPathConstants.STRING);
    }

    /**
     * Retrieve the text content of the field value element for the given field name from the
     * first (and assumed only) {@code <FieldValues>} block in the document. The field key is
     * resolved by XPath from the {@code <Fields>} definition section and the value element is
     * located via the DOM API to avoid XPath concatenation.
     *
     * <p>Asserts that exactly one {@code <FieldValues>} block exists, that the key attribute is
     * non-empty, and that exactly one value element for that key exists.
     *
     * @param doc       the EDRM XML document under test
     * @param fieldName the human-readable field name used in the {@code <Fields>} definition
     * @return the text content of the serialized field value element
     */
    private String getFieldValueText(Document doc, String fieldName) {
        String key = xpathStr(doc, "//Fields/Field[@Name='" + fieldName + "']/@Key");
        assertFalse(key.isEmpty(),
                "Expected a non-empty Key attribute on the '" + fieldName + "' field definition, got: '" + key + "'");

        NodeList valueBlocks = xpath(doc, "//FieldValues");
        assertEquals(1, valueBlocks.getLength(),
                "Expected exactly one <FieldValues> block for a single-entry document, got " + valueBlocks.getLength());

        org.w3c.dom.Element fieldValuesEl = (org.w3c.dom.Element) valueBlocks.item(0);
        org.w3c.dom.NodeList keyNodes = fieldValuesEl.getElementsByTagName(key);
        assertEquals(1, keyNodes.getLength(),
                "Expected exactly one <" + key + "> element inside <FieldValues> for field '" + fieldName + "'");
        return keyNodes.item(0).getTextContent();
    }

    /** Build a minimal EDRMBuilder (non-NLI) with a per-call temp file as the output path.
     *  Using a unique temp file per invocation makes the suite safe for parallel execution —
     *  a shared "scratch.xml" path would cause test collisions when tests run concurrently.
     */
    private EDRMBuilder newBuilder() {
        try {
            Path tempOut = Files.createTempFile(outputDir(), "edrm_scratch_", ".xml");
            tempOut.toFile().deleteOnExit();
            EDRMBuilder b = new EDRMBuilder();
            b.setAsNli(false);
            b.setOutputPath(tempOut);
            return b;
        } catch (java.io.IOException e) {
            throw new RuntimeException("Failed to create temp output file for EDRMBuilder", e);
        }
    }

    // ---- keep original tests passing ----


    @Test
    public void testSimpleFile() {
        Path sampleFile = resources().resolve("top-level-MD5-digests.txt");
        EDRMBuilder builder = new EDRMBuilder();
        builder.setAsNli(false);
        Path out = outputDir().resolve("edrm_test.xml");
        builder.setOutputPath(out);
        builder.addEntry(new FileEntry(sampleFile.toString(), "plain/text"));
        builder.save();
        assertTrue(Files.exists(out));
    }

    @Test
    public void testSimpleDirectory() {
        Path sampleDir = resources().resolve("certificates");
        EDRMBuilder builder = new EDRMBuilder();
        builder.setAsNli(false);
        Path out = outputDir().resolve("dir_test.xml");
        builder.setOutputPath(out);
        builder.addEntry(new DirectoryEntry(sampleDir.toString()));
        builder.save();
        assertTrue(Files.exists(out));
    }

    @Test
    public void testSimpleMapping() {
        Map<String, Object> map = Map.of("a", 1, "b", 2);
        EDRMBuilder builder = new EDRMBuilder();
        builder.setAsNli(false);
        Path out = outputDir().resolve("map_test.xml");
        builder.setOutputPath(out);
        builder.addEntry(new MappingEntry(map, "application/x-database-table-row"));
        builder.save();
        assertTrue(Files.exists(out));
    }

    // ---- new field type roundtrip tests ----

    /**
     * Verifies that a String-valued field is serialized with DataType="Text" in the EDRM XML
     * field definitions section. The assertion targets the specific "Subject" field by name via
     * XPath so that it cannot be satisfied by the automatically-added "MIME Type" or "Name"
     * fields (which are also Text-typed).
     */
    @Test
    public void testTextFieldRoundtrip() {
        MappingEntry entry = new MappingEntry(Map.of("Subject", "Hello World"), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();

        String dataType = xpathStr(doc, "//Fields/Field[@Name='Subject']/@DataType");
        assertEquals("Text", dataType,
                "Expected the 'Subject' field definition to have DataType=\"Text\"");

        // Also verify the serialized field value — a DataType-only assertion cannot catch
        // bugs in EntryField.serializeValue() that produce wrong or missing values.
        String value = getFieldValueText(doc, "Subject");
        assertEquals("Hello World", value,
                "Expected 'Subject' field value to be serialized as 'Hello World'");
    }

    @Test
    public void testDateTimeFieldRoundtrip() {
        OffsetDateTime knownDate = OffsetDateTime.of(2024, 6, 15, 10, 30, 0, 0, ZoneOffset.UTC);
        MappingEntry entry = new MappingEntry(Map.of("EventTime", knownDate), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();

        String dataType = xpathStr(doc, "//Fields/Field[@Name='EventTime']/@DataType");
        assertEquals("DateTime", dataType,
                "Expected DataType=\"DateTime\" on the EventTime field definition");

        // The formatted date should contain the year — use the DOM-safe helper to get the value
        String fieldValue = getFieldValueText(doc, "EventTime");
        assertTrue(fieldValue.contains("2024"),
                "Expected year '2024' in serialized EventTime value, got: '" + fieldValue + "'");
    }

    @Test
    public void testIntegerFieldRoundtrip() {
        MappingEntry entry = new MappingEntry(Map.of("RecordCount", 42L), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();

        String dataType = xpathStr(doc, "//Fields/Field[@Name='RecordCount']/@DataType");
        assertEquals("LongInteger", dataType,
                "Expected DataType=\"LongInteger\" on the RecordCount field definition");

        String fieldValue = getFieldValueText(doc, "RecordCount");
        assertEquals("42", fieldValue,
                "Expected RecordCount field value to be '42', got: '" + fieldValue + "'");
    }

    @Test
    public void testBooleanFieldRoundtrip() {
        MappingEntry entry = new MappingEntry(Map.of("IsActive", true), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();

        String dataType = xpathStr(doc, "//Fields/Field[@Name='IsActive']/@DataType");
        assertEquals("Boolean", dataType,
                "Expected DataType=\"Boolean\" on the IsActive field definition");

        // SLC-239: include the actual key value in the failure message for diagnostics
        String isActiveKey = xpathStr(doc, "//Fields/Field[@Name='IsActive']/@Key");
        assertFalse(isActiveKey.isEmpty(),
                "Expected a non-empty Key attribute on the IsActive field definition, got: '" + isActiveKey + "'");

        String fieldValue = getFieldValueText(doc, "IsActive");
        assertEquals("true", fieldValue,
                "Expected IsActive field value to be 'true', got: '" + fieldValue + "'");
    }

    @Test
    public void testDecimalFieldRoundtrip() {
        // 3.14 is a Java double literal; FieldFactory maps Double → EntryField.Type.Decimal,
        // which is serialised as DataType="Decimal" in the EDRM XML.
        // If this assertion breaks, check FieldFactory's type-dispatch table.
        MappingEntry entry = new MappingEntry(Map.of("Score", 3.14), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();

        String dataType = xpathStr(doc, "//Fields/Field[@Name='Score']/@DataType");
        assertEquals("Decimal", dataType,
                "Expected DataType=\"Decimal\" on the Score field definition");

        // EntryField serializes Double via String.format("%.4f", d), so 3.14 → "3.1400".
        // Assert via targeted DOM lookup rather than a substring match on the whole XML.
        String fieldValue = getFieldValueText(doc, "Score");
        assertTrue(fieldValue.contains("3.14"),
                "Expected Score field value to contain '3.14', got: '" + fieldValue + "'");
    }

    @Test
    public void testLongTextFieldRoundtrip() {
        // Manually add a LongText field to a MappingEntry
        MappingEntry entry = new MappingEntry(Map.of("Name", "sample"), "text/plain");
        entry.putField(FieldFactory.generateField("Description", EntryField.Type.LongText, "A long text value"));
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();

        String dataType = xpathStr(doc, "//Fields/Field[@Name='Description']/@DataType");
        assertEquals("LongText", dataType,
                "Expected DataType=\"LongText\" on the Description field definition");

        String fieldValue = getFieldValueText(doc, "Description");
        assertEquals("A long text value", fieldValue,
                "Expected Description field value to be 'A long text value', got: '" + fieldValue + "'");
    }

    // ---- relationship and structure tests ----

    @Test
    public void testParentChildRelationship() {
        EDRMBuilder builder = newBuilder();
        MappingEntry parent = new MappingEntry(Map.of("Name", "Parent"), "text/plain");
        String parentId = builder.addEntry(parent);

        MappingEntry child = new MappingEntry(Map.of("Name", "Child"), "text/plain", parentId);
        String childId = builder.addEntry(child);

        Document doc = builder.build();

        // Verify the Relationships section has a Relationship element with the correct parent/child
        NodeList relationships = xpath(doc, "//Relationship");
        assertTrue(relationships.getLength() > 0,
                "Expected at least one <Relationship> element in EDRM XML");

        boolean foundRelationship = false;
        for (int i = 0; i < relationships.getLength(); i++) {
            org.w3c.dom.Element rel = (org.w3c.dom.Element) relationships.item(i);
            if (parentId.equals(rel.getAttribute("ParentDocId")) && childId.equals(rel.getAttribute("ChildDocId"))) {
                foundRelationship = true;
                break;
            }
        }
        assertTrue(foundRelationship,
                "Expected Relationship with ParentDocId=" + parentId + " and ChildDocId=" + childId);
    }

    @Test
    public void testDirectoryParentPath() throws java.io.IOException {
        // Use a self-contained temp directory so the test has no dependency on fixture files
        Path tempDir = Files.createTempDirectory("edrm_dir_test");
        Path tempFile = Files.createTempFile(tempDir, "sample", ".txt");
        try {
            Files.writeString(tempFile, "test content");

            EDRMBuilder builder = newBuilder();
            builder.setAsNli(true); // NLI mode so LocationURI uses relative path

            DirectoryEntry dir = new DirectoryEntry(tempDir.toString());
            String dirId = builder.addEntry(dir);

            FileEntry child = new FileEntry(tempFile.toString(), "text/plain", dirId);
            builder.addEntry(child);

            Document doc = builder.build();
            String xml = docToString(doc);

            // The LocationURI for the child entry should contain the directory name as a path prefix
            String dirName = tempDir.getFileName().toString();
            assertTrue(xml.contains(dirName),
                    "Expected temp directory name '" + dirName + "' in LocationURI (relative path), but got:\n" + xml);
        } finally {
            Files.deleteIfExists(tempFile);
            Files.deleteIfExists(tempDir);
        }
    }

    /** Save and restore all config keys mutated during a test. */
    private final java.util.Map<String, String> savedConfigKeys = new java.util.LinkedHashMap<>();

    private void saveConfig(String... keys) {
        for (String key : keys) {
            savedConfigKeys.put(key, EDRMUtilities.EDRM_CONFIG.get(key));
        }
    }

    @AfterEach
    public void restoreConfig() {
        // Restore every key that was saved by saveConfig() during the test
        for (java.util.Map.Entry<String, String> entry : savedConfigKeys.entrySet()) {
            if (entry.getValue() == null) {
                EDRMUtilities.EDRM_CONFIG.remove(entry.getKey());
            } else {
                EDRMUtilities.EDRM_CONFIG.put(entry.getKey(), entry.getValue());
            }
        }
        savedConfigKeys.clear();
    }

    @Test
    public void testCustodianDefault() {
        // Remove the custodian key entirely so the code must fall back to its hardcoded default.
        // This tests that addLocation() uses getOrDefault("custodian", "Unknown") rather than
        // reading a value that happens to already equal the default in edrm.config.
        saveConfig("custodian");
        EDRMUtilities.EDRM_CONFIG.remove("custodian");

        EDRMBuilder builder = newBuilder();
        builder.addEntry(new MappingEntry(Map.of("Name", "Test"), "text/plain"));
        Document doc = builder.build();

        // Use XPath to target the specific <Custodian> element in the Location section
        NodeList custodianNodes = xpath(doc, "//Location/Custodian");
        assertTrue(custodianNodes.getLength() > 0,
                "Expected at least one <Custodian> element under <Location>");
        assertEquals("Unknown", custodianNodes.item(0).getTextContent(),
                "Expected fallback custodian value 'Unknown' when key is absent from config");
    }

    @Test
    public void testCustodianOverride() {
        saveConfig("custodian");
        EDRMUtilities.EDRM_CONFIG.put("custodian", "Alice");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(new MappingEntry(Map.of("Name", "Test"), "text/plain"));
        Document doc = builder.build();

        // Use XPath to confirm the specific <Custodian> element contains the overridden value
        NodeList custodianNodes = xpath(doc, "//Location/Custodian");
        assertTrue(custodianNodes.getLength() > 0,
                "Expected at least one <Custodian> element under <Location>");
        assertEquals("Alice", custodianNodes.item(0).getTextContent(),
                "Expected custodian text content to be 'Alice'");
    }

    @Test
    public void testMultipleEntries() {
        EDRMBuilder builder = newBuilder();
        for (int i = 1; i <= 5; i++) {
            builder.addEntry(new MappingEntry(Map.of("Name", "Entry" + i, "Index", (long) i), "text/plain"));
        }
        Document doc = builder.build();

        NodeList documents = xpath(doc, "//Documents/Document");
        assertEquals(5, documents.getLength(),
                "Expected exactly 5 <Document> elements in <Documents>, but found " + documents.getLength());
    }

    @Test
    public void testFieldDefinitionsSection() {
        EDRMBuilder builder = newBuilder();
        // All entries share a common field "Name" — it should appear only once in <Fields>
        for (int i = 1; i <= 3; i++) {
            builder.addEntry(new MappingEntry(Map.of("Name", "Entry" + i), "text/plain"));
        }
        Document doc = builder.build();

        // Count Field elements with Name="Name" — should be exactly 1 due to dedup in serializeDefinition
        NodeList fieldDefs = xpath(doc, "//Fields/Field[@Name='Name']");
        assertEquals(1, fieldDefs.getLength(),
                "Expected the 'Name' field definition to appear exactly once in <Fields>, but found " + fieldDefs.getLength());

        // Count Field elements with Name="MIME Type" — should also be exactly 1
        NodeList mimeTypeDefs = xpath(doc, "//Fields/Field[@Name='MIME Type']");
        assertEquals(1, mimeTypeDefs.getLength(),
                "Expected 'MIME Type' field definition to appear exactly once in <Fields>, but found " + mimeTypeDefs.getLength());
    }

    // ---- edge case tests (SLC-70) ----

    /**
     * Builds an EDRM document with no entries and verifies the output contains an empty
     * {@code <Documents>} section and an empty {@code <Fields>} section (no child elements).
     */
    @Test
    public void testEmptyBuilder() {
        EDRMBuilder builder = newBuilder();
        Document doc = builder.build();

        // <Documents> must exist but have no <Document> children
        NodeList documents = xpath(doc, "//Documents/Document");
        assertEquals(0, documents.getLength(),
                "Expected zero <Document> elements in an empty builder, found " + documents.getLength());

        // <Fields> must exist but have no <Field> children
        NodeList fields = xpath(doc, "//Fields/Field");
        assertEquals(0, fields.getLength(),
                "Expected zero <Field> elements in an empty builder, found " + fields.getLength());
    }

    /**
     * Verifies that XML special characters ({@code <}, {@code >}, {@code &}) in a field value are
     * properly XML-escaped in the serialized output. The DOM {@code createTextNode} path (used by
     * {@link com.nuix.edrm.EntryField#serializeValue}) escapes these automatically, so the raw
     * string representation should never appear in the XML bytes.
     *
     * <p>Note: {@code "} and {@code '} are not asserted here because the DOM serializer does not
     * escape them in text nodes (only in attribute values), so they pass through unmodified.
     */
    @Test
    public void testXmlSpecialCharsInFieldValue() {
        String rawValue = "<script>alert('hello & \"world\"')</script>";
        MappingEntry entry = new MappingEntry(Map.of("Payload", rawValue), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();
        String xml = docToString(doc);

        // The raw angle brackets and ampersand must not appear in the serialized XML
        assertFalse(xml.contains("<script>"),
                "Unescaped '<script>' tag must not appear in serialized XML output");
        assertFalse(xml.contains("alert("),
                "Unescaped '<script>' content must not appear in serialized XML output");

        // The XML-escaped forms must be present
        assertTrue(xml.contains("&lt;script&gt;"),
                "Expected '&lt;script&gt;' (escaped '<script>') in XML output, got:\n" + xml);
        assertTrue(xml.contains("&amp;"),
                "Expected '&amp;' (escaped '&') in XML output, got:\n" + xml);
    }

    /**
     * Verifies that when two different entries both carry a field with the same name but different
     * values, the {@code <Fields>} definitions section still lists that field name exactly once.
     * This exercises the deduplication logic in
     * {@link com.nuix.edrm.EntryField#serializeDefinition}.
     */
    @Test
    public void testDuplicateFieldName() {
        EDRMBuilder builder = newBuilder();
        builder.addEntry(new MappingEntry(Map.of("Status", "active"), "text/plain"));
        builder.addEntry(new MappingEntry(Map.of("Status", "inactive"), "text/plain"));
        Document doc = builder.build();

        // "Status" must appear exactly once in the <Fields> definitions section
        NodeList statusFields = xpath(doc, "//Fields/Field[@Name='Status']");
        assertEquals(1, statusFields.getLength(),
                "Expected 'Status' field definition to appear exactly once in <Fields> even when "
                + "two entries carry the same field name, but found " + statusFields.getLength());

        // Both entries' field values must still be present in the <Documents> section.
        // The key-based element name is resolved from the <Fields> definition to avoid
        // coupling the test to internal key-generation order (field_1, field_2, …).
        String statusKey = xpathStr(doc, "//Fields/Field[@Name='Status']/@Key");
        NodeList activeVals = xpath(doc, "//Documents/Document/FieldValues/" + statusKey + "[text()='active']");
        assertEquals(1, activeVals.getLength(),
                "Expected one Document with Status='active' in <FieldValues>, but found " + activeVals.getLength());

        NodeList inactiveVals = xpath(doc, "//Documents/Document/FieldValues/" + statusKey + "[text()='inactive']");
        assertEquals(1, inactiveVals.getLength(),
                "Expected one Document with Status='inactive' in <FieldValues>, but found " + inactiveVals.getLength());
    }
}
