package com.nuix.nli;

import com.nuix.nli.edrm.DirectoryEntry;
import com.nuix.nli.edrm.EDRMBuilder;
import com.nuix.nli.edrm.FileEntry;
import com.nuix.nli.edrm.MappingEntry;
import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertTrue;

public class EdrmTests {
    private Path resources() { return Paths.get(".", "src", "test", "resources").toAbsolutePath().normalize(); }
    private Path outputDir() { return Paths.get("build", "test-output").toAbsolutePath().normalize(); }

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
}