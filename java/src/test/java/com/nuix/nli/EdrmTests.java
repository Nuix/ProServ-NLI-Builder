package com.nuix.nli;

import com.nuix.edrm.DirectoryEntry;
import com.nuix.edrm.EDRMBuilder;
import com.nuix.edrm.FileEntry;
import com.nuix.edrm.MappingEntry;
import org.junit.jupiter.api.Test;
import org.w3c.dom.Document;

import javax.xml.xpath.XPath;
import javax.xml.xpath.XPathFactory;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

public class EdrmTests {
    private Path resources() { return Paths.get(".", "src", "test", "resources").toAbsolutePath().normalize(); }
    private Path outputDir() { return Paths.get("build", "test-output").toAbsolutePath().normalize(); }

    /**
     * Evaluate an XPath expression against a Document and return the string result.
     */
    private String xpath(Document doc, String expression) throws Exception {
        XPath xp = XPathFactory.newInstance().newXPath();
        return xp.evaluate(expression, doc);
    }

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
        Map<String,Object> map = Map.of("a",1, "b", 2);
        EDRMBuilder builder = new EDRMBuilder();
        builder.setAsNli(false);
        Path out = outputDir().resolve("map_test.xml");
        builder.setOutputPath(out);
        builder.addEntry(new MappingEntry(map, "application/x-database-table-row"));
        builder.save();
        assertTrue(Files.exists(out));
    }

    /**
     * Verifies that a String-valued field is serialized with DataType="Text" in the EDRM XML
     * field definitions section. The assertion targets the specific "Subject" field by name via
     * XPath so that it cannot be satisfied by the automatically-added "MIME Type" or "Name"
     * fields (which are also Text-typed and would make a naive xml.contains("DataType=\"Text\"")
     * pass even if "Subject" were never emitted.
     */
    @Test
    public void testTextFieldRoundtrip() throws Exception {
        Map<String, Object> data = Map.of("Subject", "Hello World");
        EDRMBuilder builder = new EDRMBuilder();
        builder.setAsNli(false);
        builder.addEntry(new MappingEntry(data, "application/x-database-table-row"));
        Document doc = builder.build();

        String dataType = xpath(doc, "//Fields/Field[@Name='Subject']/@DataType");
        assertEquals("Text", dataType,
                "Expected the 'Subject' field definition to have DataType=\"Text\"");
    }
}