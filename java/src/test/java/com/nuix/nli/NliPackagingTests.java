package com.nuix.nli;

import com.nuix.edrm.FileEntry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HashSet;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

import static org.junit.jupiter.api.Assertions.*;

public class NliPackagingTests {

    private Path resources() {
        return Paths.get(".", "src", "test", "resources").toAbsolutePath().normalize();
    }

    /**
     * Opens an .nli file as a ZIP stream and returns the set of all entry names contained within.
     */
    private Set<String> listNliEntries(Path nliPath) throws IOException {
        Set<String> entries = new HashSet<>();
        try (InputStream fis = Files.newInputStream(nliPath);
             ZipInputStream zis = new ZipInputStream(fis)) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                entries.add(entry.getName());
                zis.closeEntry();
            }
        }
        return entries;
    }

    /**
     * Reads the raw bytes of a named entry inside an .nli (ZIP) file.
     */
    private byte[] readNliEntry(Path nliPath, String entryName) throws IOException {
        try (InputStream fis = Files.newInputStream(nliPath);
             ZipInputStream zis = new ZipInputStream(fis)) {
            ZipEntry entry;
            while ((entry = zis.getNextEntry()) != null) {
                if (entryName.equals(entry.getName())) {
                    return zis.readAllBytes();
                }
                zis.closeEntry();
            }
        }
        throw new IOException("Entry not found in NLI ZIP: " + entryName);
    }

    @Test
    public void testZipContainsMetadataXml(@TempDir Path tempDir) throws IOException {
        Path sampleFile = resources().resolve("top-level-MD5-digests.txt");
        NLIGenerator generator = new NLIGenerator();
        generator.addEntry(new FileEntry(sampleFile.toString(), "text/plain"));

        Path nliPath = tempDir.resolve("output.nli");
        generator.save(nliPath);

        assertTrue(Files.exists(nliPath), "NLI file should exist after save()");

        Set<String> entries = listNliEntries(nliPath);
        assertTrue(
            entries.contains("._metadata/image_contents.xml"),
            "NLI ZIP should contain '._metadata/image_contents.xml', found: " + entries
        );
    }

    @Test
    public void testZipContainsSha1Sidecar(@TempDir Path tempDir) throws IOException {
        Path sampleFile = resources().resolve("top-level-MD5-digests.txt");
        NLIGenerator generator = new NLIGenerator();
        generator.addEntry(new FileEntry(sampleFile.toString(), "text/plain"));

        Path nliPath = tempDir.resolve("output.nli");
        generator.save(nliPath);

        Set<String> entries = listNliEntries(nliPath);
        assertTrue(
            entries.contains("._metadata/image_contents.sha1_hash"),
            "NLI ZIP should contain '._metadata/image_contents.sha1_hash', found: " + entries
        );

        // Verify the sha1_hash bytes match the SHA-1 of image_contents.xml
        byte[] xmlBytes = readNliEntry(nliPath, "._metadata/image_contents.xml");
        byte[] storedHash = readNliEntry(nliPath, "._metadata/image_contents.sha1_hash");

        byte[] expectedHash;
        try {
            MessageDigest sha1 = MessageDigest.getInstance("SHA-1");
            expectedHash = sha1.digest(xmlBytes);
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }

        assertArrayEquals(
            expectedHash,
            storedHash,
            "SHA-1 sidecar contents should match the SHA-1 hash of image_contents.xml"
        );
    }

    @Test
    public void testZipContainsNativeFile(@TempDir Path tempDir) throws IOException {
        Path sampleFile = resources().resolve("top-level-MD5-digests.txt");
        NLIGenerator generator = new NLIGenerator();
        generator.addEntry(new FileEntry(sampleFile.toString(), "text/plain"));

        Path nliPath = tempDir.resolve("output.nli");
        generator.save(nliPath);

        // A FileEntry with no parent is placed at the root of NLI_Gen using just the filename.
        String expectedEntryName = sampleFile.getFileName().toString();

        Set<String> entries = listNliEntries(nliPath);
        assertTrue(
            entries.contains(expectedEntryName),
            "NLI ZIP should contain native file '" + expectedEntryName + "', found: " + entries
        );
    }
}
