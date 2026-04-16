package com.nuix.nli;

import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.EntryField;
import com.nuix.edrm.EntryInterface;
import com.nuix.edrm.datatypes.JSONFileEntry;
import com.nuix.edrm.datatypes.JSONObjectEntry;
import com.nuix.edrm.datatypes.JSONValueEntry;
import org.junit.jupiter.api.Test;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

public class JsonTests {
    private Path resources() { return Paths.get("..", "python", "test", "resources").toAbsolutePath().normalize(); }
    private Path outputDir() { return Paths.get("build", "test-output", "json").toAbsolutePath().normalize(); }

    // -------------------------------------------------------------------------
    // Existing smoke test
    // -------------------------------------------------------------------------

    @Test
    public void testSimpleStr() {
        Path json = resources().resolve("simple_str.json");
        JSONFileEntry entry = new JSONFileEntry(json.toString());
        NLIGenerator nli = new NLIGenerator();
        nli.addEntry(entry);
        if (outputDir().toFile().exists() == false) outputDir().toFile().mkdirs();
        Path out = outputDir().resolve("simple_str.nli");
        nli.save(out);
        assertTrue(Files.exists(out));
    }

    // -------------------------------------------------------------------------
    // Structural content tests (SLC-68)
    // -------------------------------------------------------------------------

    /**
     * testObjectFieldCount: Load object_mixed.json (4 top-level keys).
     * Assert the JSONObjectEntry child exposes exactly 4 data fields.
     */
    @Test
    public void testObjectFieldCount() {
        Path json = resources().resolve("object_mixed.json");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        String fileId = fileEntry.addToBuilder(builder);

        // Find the JSONObjectEntry child
        JSONObjectEntry objectEntry = findChildOfType(builder, fileId, JSONObjectEntry.class);
        assertNotNull(objectEntry, "Expected a JSONObjectEntry child for a JSON object file");

        // object_mixed.json has 4 keys: "key 1", "key 2", "key 3", "key 4"
        assertEquals(4, objectEntry.getDataFieldCount(),
                "JSONObjectEntry should expose 4 data fields matching the JSON object keys");
    }

    /**
     * testArrayChildCount: Load list_mixed.json (4 array elements).
     * Assert the builder contains exactly 4 JSONValueEntry children.
     */
    @Test
    public void testArrayChildCount() {
        Path json = resources().resolve("list_mixed.json");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        String fileId = fileEntry.addToBuilder(builder);

        List<JSONValueEntry> valueEntries = findChildrenOfType(builder, fileId, JSONValueEntry.class);
        // list_mixed.json: ["value 1", 2, 3.01, false]
        assertEquals(4, valueEntries.size(),
                "JSONValueEntry children should equal the number of array elements (4)");
    }

    /**
     * testNestedObjectCreatesChild: Load object_complex.json (a JSON object with nested sub-objects).
     * Assert the parent JSONFileEntry has exactly one child entry (JSONObjectEntry) in the familyMap.
     * Nested sub-objects are inlined as string fields within the single child entry rather than
     * creating additional deeply-nested entries.
     */
    @Test
    public void testNestedObjectCreatesChild() {
        Path json = resources().resolve("object_complex.json");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        String fileId = fileEntry.addToBuilder(builder);

        Map<String, List<String>> familyMap = builder.getFamilyMap();
        List<String> children = familyMap.getOrDefault(fileId, List.of());
        assertEquals(1, children.size(),
                "A JSON object file (including those with nested sub-objects) should produce exactly one JSONObjectEntry child in the family map");

        // Verify the child is a JSONObjectEntry
        JSONObjectEntry objectEntry = findChildOfType(builder, fileId, JSONObjectEntry.class);
        assertNotNull(objectEntry, "The single child should be a JSONObjectEntry");
    }

    /**
     * testScalarTypes: Load object_mixed.json (string, int, float, bool values).
     * Assert each field in the JSONObjectEntry has the correct EntryField.Type.
     */
    @Test
    public void testScalarTypes() {
        Path json = resources().resolve("object_mixed.json");
        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        String fileId = fileEntry.addToBuilder(builder);

        JSONObjectEntry objectEntry = findChildOfType(builder, fileId, JSONObjectEntry.class);
        assertNotNull(objectEntry, "Expected a JSONObjectEntry child");

        // object_mixed.json: "key 1"->string, "key 2"->int, "key 3"->float, "key 4"->bool
        assertEquals(EntryField.Type.Text, objectEntry.getField("key 1").getDataType(),
                "String value should map to EntryField.Type.Text");
        assertEquals(EntryField.Type.LongInteger, objectEntry.getField("key 2").getDataType(),
                "Integer value should map to EntryField.Type.LongInteger");
        assertEquals(EntryField.Type.Decimal, objectEntry.getField("key 3").getDataType(),
                "Float value should map to EntryField.Type.Decimal");
        assertEquals(EntryField.Type.Boolean, objectEntry.getField("key 4").getDataType(),
                "Boolean value should map to EntryField.Type.Boolean");
    }

    /**
     * testParentIdPropagation: Build EDRM XML from simple_str.json.
     * Assert every Relationship element in the XML has ParentDocId equal to
     * the JSONFileEntry's identifier (SHA-1).
     */
    @Test
    public void testParentIdPropagation() {
        Path json = resources().resolve("simple_str.json");
        EDRMBuilder builder = new EDRMBuilder();
        builder.setAsNli(false);

        JSONFileEntry fileEntry = new JSONFileEntry(json.toString());
        String fileId = fileEntry.addToBuilder(builder);

        // Build the EDRM XML and inspect the <Relationships> section
        Document doc = builder.build();
        NodeList relationships = doc.getElementsByTagName("Relationship");

        assertTrue(relationships.getLength() > 0,
                "Expected at least one Relationship element in the EDRM XML");

        for (int i = 0; i < relationships.getLength(); i++) {
            Element rel = (Element) relationships.item(i);
            String parentDocId = rel.getAttribute("ParentDocId");
            assertEquals(fileId, parentDocId,
                    "ParentDocId in <Relationship> should equal the JSONFileEntry's SHA-1 identifier");
        }
    }

    // -------------------------------------------------------------------------
    // Missing tests from SLC-65 acceptance criteria (SLC-80)
    // -------------------------------------------------------------------------

    /**
     * testNullValue: JSON file whose entire content is the literal {@code null}.
     *
     * <p>The scalar branch in {@link JSONFileEntry#addToBuilder} should produce exactly
     * one {@link JSONValueEntry} child with {@code getRawValue() == null}. No NPE should
     * be thrown during parsing or field population.
     */
    @Test
    public void testNullValue() throws Exception {
        // Write a minimal JSON null document to a temp file in the output dir
        Path tempJson = outputDir().resolve("null_value.json");
        outputDir().toFile().mkdirs();
        Files.writeString(tempJson, "null", StandardCharsets.UTF_8);

        EDRMBuilder builder = new EDRMBuilder();
        JSONFileEntry fileEntry = new JSONFileEntry(tempJson.toString());
        String fileId = fileEntry.addToBuilder(builder);

        // Exactly one child: the scalar null represented as a JSONValueEntry
        Map<String, List<String>> familyMap = builder.getFamilyMap();
        List<String> children = familyMap.getOrDefault(fileId, List.of());
        assertEquals(1, children.size(),
                "A JSON null root should produce exactly one JSONValueEntry child");

        // The child is a JSONValueEntry
        JSONValueEntry valueEntry = findChildOfType(builder, fileId, JSONValueEntry.class);
        assertNotNull(valueEntry, "Child of a JSON null root should be a JSONValueEntry");

        // getRawValue() must be null — no NPE during construction or here
        assertNull(valueEntry.getRawValue(),
                "JSONValueEntry.getRawValue() should be null for a JSON null root");
    }

    /**
     * testCustomRootFactory: Subclass {@link JSONFileEntry} and override
     * {@link JSONFileEntry#createObjectRoot} to inject a custom {@link JSONObjectEntry}
     * subclass. Assert that the builder contains the custom subclass instance, not the
     * default {@link JSONObjectEntry}.
     */
    @Test
    public void testCustomRootFactory() {
        // A minimal custom subclass that tags itself so it can be identified in the builder
        class TaggedObjectEntry extends JSONObjectEntry {
            final String tag;
            TaggedObjectEntry(Map<String, Object> fields, String parentId) {
                super(fields, parentId);
                this.tag = "custom-factory";
            }
        }

        // Override createObjectRoot to return a TaggedObjectEntry instead of the default
        JSONFileEntry customEntry = new JSONFileEntry(resources().resolve("object_mixed.json").toString()) {
            @Override
            protected JSONObjectEntry createObjectRoot(Map<String, Object> fields, String parentId) {
                return new TaggedObjectEntry(fields, parentId);
            }
        };

        EDRMBuilder builder = new EDRMBuilder();
        String fileId = customEntry.addToBuilder(builder);

        // The builder should have registered a TaggedObjectEntry, not a plain JSONObjectEntry
        TaggedObjectEntry tagged = findChildOfType(builder, fileId, TaggedObjectEntry.class);
        assertNotNull(tagged,
                "createObjectRoot override should produce a TaggedObjectEntry in the builder");
        assertEquals("custom-factory", tagged.tag,
                "Custom subclass identity should be preserved through the factory method");
    }

    /**
     * testDeepNesting: Verify that the EDRM relationship chain contains 3 distinct levels
     * when a {@link JSONFileEntry} is registered as a child of a root {@link com.nuix.edrm.FileEntry}.
     *
     * <p>The chain is: {@code rootFile} → {@code JSONFileEntry} → {@code JSONObjectEntry}.
     * The test inspects the {@code <Relationship>} elements in the EDRM XML output and
     * confirms that the ChildDocId of the first relationship is the ParentDocId of the second,
     * forming an unambiguous 3-node parent chain (level 1 → level 2 → level 3).
     */
    @Test
    public void testDeepNesting() {
        // Build a 3-level hierarchy:
        //   Level 1: root FileEntry (a plain file acting as the top-level parent)
        //   Level 2: JSONFileEntry registered as a child of the root file
        //   Level 3: JSONObjectEntry created automatically by addToBuilder (child of JSONFileEntry)
        Path jsonPath = resources().resolve("object_mixed.json");
        EDRMBuilder builder = new EDRMBuilder();
        builder.setAsNli(false);

        // Level 1: add the JSON file itself as a plain FileEntry (no parent)
        String rootId = builder.addFile(jsonPath.toString(), "application/json");

        // Level 2: add a JSONFileEntry pointing at object_mixed.json, parented to rootId
        JSONFileEntry fileEntry = new JSONFileEntry(jsonPath.toString(), "application/json", rootId);
        String fileId = fileEntry.addToBuilder(builder);

        // Level 3: JSONObjectEntry is added automatically by addToBuilder as a child of fileId
        JSONObjectEntry objectEntry = findChildOfType(builder, fileId, JSONObjectEntry.class);
        assertNotNull(objectEntry, "JSONObjectEntry child must be present for an object JSON root");
        String objectId = objectEntry.getField(objectEntry.getIdentifierField()).getValue().toString();

        // Build and inspect the EDRM XML <Relationships> section
        Document doc = builder.build();
        NodeList relationships = doc.getElementsByTagName("Relationship");
        assertTrue(relationships.getLength() >= 2,
                "A 3-level chain requires at least 2 <Relationship> elements");

        // Verify both links of the 3-level chain are present in the XML
        boolean foundRootToFile   = false;
        boolean foundFileToObject = false;
        for (int i = 0; i < relationships.getLength(); i++) {
            Element rel = (Element) relationships.item(i);
            String parent = rel.getAttribute("ParentDocId");
            String child  = rel.getAttribute("ChildDocId");
            if (rootId.equals(parent)  && fileId.equals(child))   foundRootToFile   = true;
            if (fileId.equals(parent)  && objectId.equals(child)) foundFileToObject = true;
        }

        assertTrue(foundRootToFile,
                "Expected a Relationship from root FileEntry (level 1) to JSONFileEntry (level 2)");
        assertTrue(foundFileToObject,
                "Expected a Relationship from JSONFileEntry (level 2) to JSONObjectEntry (level 3)");
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    /** Finds the first child of {@code parentId} whose entry is an instance of {@code type}. */
    @SuppressWarnings("unchecked")
    private <T extends EntryInterface> T findChildOfType(EDRMBuilder builder, String parentId, Class<T> type) {
        Map<String, List<String>> familyMap = builder.getFamilyMap();
        List<String> children = familyMap.getOrDefault(parentId, List.of());
        Map<String, EntryInterface> entryMap = builder.getEntryMap();
        for (String childId : children) {
            EntryInterface entry = entryMap.get(childId);
            if (type.isInstance(entry)) {
                return (T) entry;
            }
        }
        return null;
    }

    /** Finds all children of {@code parentId} whose entries are instances of {@code type}. */
    @SuppressWarnings("unchecked")
    private <T extends EntryInterface> List<T> findChildrenOfType(EDRMBuilder builder, String parentId, Class<T> type) {
        Map<String, List<String>> familyMap = builder.getFamilyMap();
        List<String> children = familyMap.getOrDefault(parentId, List.of());
        Map<String, EntryInterface> entryMap = builder.getEntryMap();
        List<T> result = new ArrayList<>();
        for (String childId : children) {
            EntryInterface entry = entryMap.get(childId);
            if (type.isInstance(entry)) {
                result.add((T) entry);
            }
        }
        return result;
    }
}