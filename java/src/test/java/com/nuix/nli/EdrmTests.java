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
import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathConstants;
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

    /** Evaluate an XPath expression returning a NodeList against a Document. */
    private NodeList xpath(Document doc, String expression) {
        try {
            XPath xp = XPathFactory.newInstance().newXPath();
            return (NodeList) xp.evaluate(expression, doc, XPathConstants.NODESET);
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    /** Build a minimal EDRMBuilder (non-NLI) with no output path required for build(). */
    private EDRMBuilder newBuilder() {
        EDRMBuilder b = new EDRMBuilder();
        b.setAsNli(false);
        b.setOutputPath(outputDir().resolve("scratch.xml"));
        return b;
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

    @Test
    public void testTextFieldRoundtrip() {
        MappingEntry entry = new MappingEntry(Map.of("Subject", "Hello World"), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();
        String xml = docToString(doc);

        // The Fields section should declare DataType="Text" for "Subject"
        assertTrue(xml.contains("DataType=\"Text\""),
                "Expected DataType=\"Text\" in EDRM XML Fields section, but got:\n" + xml);
        assertTrue(xml.contains("Hello World"),
                "Expected field value 'Hello World' in EDRM XML, but got:\n" + xml);
    }

    @Test
    public void testDateTimeFieldRoundtrip() {
        OffsetDateTime knownDate = OffsetDateTime.of(2024, 6, 15, 10, 30, 0, 0, ZoneOffset.UTC);
        MappingEntry entry = new MappingEntry(Map.of("EventTime", knownDate), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();
        String xml = docToString(doc);

        assertTrue(xml.contains("DataType=\"DateTime\""),
                "Expected DataType=\"DateTime\" in EDRM XML Fields section, but got:\n" + xml);
        // The formatted date should contain the year
        assertTrue(xml.contains("2024"),
                "Expected year '2024' in serialized DateTime field value, but got:\n" + xml);
    }

    @Test
    public void testIntegerFieldRoundtrip() {
        MappingEntry entry = new MappingEntry(Map.of("RecordCount", 42L), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();
        String xml = docToString(doc);

        assertTrue(xml.contains("DataType=\"LongInteger\""),
                "Expected DataType=\"LongInteger\" in EDRM XML Fields section, but got:\n" + xml);
        assertTrue(xml.contains("42"),
                "Expected value '42' in EDRM XML field values, but got:\n" + xml);
    }

    @Test
    public void testBooleanFieldRoundtrip() {
        MappingEntry entry = new MappingEntry(Map.of("IsActive", true), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();
        String xml = docToString(doc);

        assertTrue(xml.contains("DataType=\"Boolean\""),
                "Expected DataType=\"Boolean\" in EDRM XML Fields section, but got:\n" + xml);
        assertTrue(xml.contains("true"),
                "Expected value 'true' in EDRM XML field values, but got:\n" + xml);
    }

    @Test
    public void testDecimalFieldRoundtrip() {
        MappingEntry entry = new MappingEntry(Map.of("Score", 3.14), "text/plain");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();
        String xml = docToString(doc);

        assertTrue(xml.contains("DataType=\"Decimal\""),
                "Expected DataType=\"Decimal\" in EDRM XML Fields section, but got:\n" + xml);
        assertTrue(xml.contains("3.14"),
                "Expected value containing '3.14' in EDRM XML field values, but got:\n" + xml);
    }

    @Test
    public void testLongTextFieldRoundtrip() {
        // Manually add a LongText field to a MappingEntry
        MappingEntry entry = new MappingEntry(Map.of("Name", "sample"), "text/plain");
        entry.putField(FieldFactory.generateField("Description", EntryField.Type.LongText, "A long text value"));
        EDRMBuilder builder = newBuilder();
        builder.addEntry(entry);
        Document doc = builder.build();
        String xml = docToString(doc);

        assertTrue(xml.contains("DataType=\"LongText\""),
                "Expected DataType=\"LongText\" in EDRM XML Fields section, but got:\n" + xml);
        assertTrue(xml.contains("A long text value"),
                "Expected LongText field value in EDRM XML, but got:\n" + xml);
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
        saveConfig("custodian");
        EDRMUtilities.EDRM_CONFIG.put("custodian", "Unknown");
        EDRMBuilder builder = newBuilder();
        builder.addEntry(new MappingEntry(Map.of("Name", "Test"), "text/plain"));
        Document doc = builder.build();

        // Use XPath to target the specific <Custodian> element in the Location section
        NodeList custodianNodes = xpath(doc, "//Location/Custodian");
        assertTrue(custodianNodes.getLength() > 0,
                "Expected at least one <Custodian> element under <Location>");
        assertEquals("Unknown", custodianNodes.item(0).getTextContent(),
                "Expected custodian text content to be 'Unknown'");
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
}
