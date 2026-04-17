package com.nuix.nli;

import com.nuix.edrm.DirectoryEntry;
import com.nuix.edrm.FileEntry;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.xml.sax.SAXException;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import java.io.ByteArrayInputStream;
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

class NliPackagingTests {

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
    void testZipContainsMetadataXml(@TempDir Path tempDir) throws IOException, ParserConfigurationException, SAXException {
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

        // Verify image_contents.xml is well-formed XML (SLC-165)
        byte[] xmlBytes = readNliEntry(nliPath, "._metadata/image_contents.xml");
        DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(new ByteArrayInputStream(xmlBytes));
    }

    @Test
    void testZipContainsSha1Sidecar(@TempDir Path tempDir) throws IOException, NoSuchAlgorithmException {
        Path sampleFile = resources().resolve("top-level-MD5-digests.txt");
        NLIGenerator generator = new NLIGenerator();
        generator.addEntry(new FileEntry(sampleFile.toString(), "text/plain"));

        Path nliPath = tempDir.resolve("output.nli");
        generator.save(nliPath);

        // Read both sidecar files directly — readNliEntry throws IOException("Entry not found
        // in NLI ZIP: ...") if either is absent, giving a clear failure signal without a
        // separate presence-only assertTrue that duplicates the check.
        byte[] xmlBytes = readNliEntry(nliPath, "._metadata/image_contents.xml");
        byte[] storedHash = readNliEntry(nliPath, "._metadata/image_contents.sha1_hash");

        // Verify the sha1_hash bytes match the SHA-1 of image_contents.xml.
        // SHA-1 is mandated by the JCA spec for every Java SE implementation, so
        // NoSuchAlgorithmException is declared but can never fire in practice.

        MessageDigest sha1 = MessageDigest.getInstance("SHA-1");
        byte[] expectedHash = sha1.digest(xmlBytes);

        assertArrayEquals(
            expectedHash,
            storedHash,
            "SHA-1 sidecar contents should match the SHA-1 hash of image_contents.xml"
        );
    }

    @Test
    void testZipContainsNativeFile(@TempDir Path tempDir) throws IOException {
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

    @Test
    void testZipContainsNativeFileInSubdirectory(@TempDir Path tempDir) throws IOException {
        // SLC-164: Cover the FileEntry-with-parent-DirectoryEntry code branch in NLIGenerator.save().
        // When a FileEntry has a parent DirectoryEntry, the generator computes the ZIP path as
        // URLEncode(dirName) + "/" + fileName instead of placing the file at the root.
        Path nativeFile = resources().resolve("top-level-MD5-digests.txt");

        // Use a self-contained subdirectory in tempDir so the DirectoryEntry hash is cheap and deterministic.
        Path subDir = tempDir.resolve("docs");
        Files.createDirectories(subDir);

        NLIGenerator generator = new NLIGenerator();
        String dirId = generator.addEntry(new DirectoryEntry(subDir.toString()));
        generator.addEntry(new FileEntry(nativeFile.toString(), "text/plain", dirId));

        Path nliPath = tempDir.resolve("output.nli");
        generator.save(nliPath);

        // The directory name "docs" URL-encodes to "docs"; the expected ZIP path is "docs/top-level-MD5-digests.txt".
        String expectedEntryName = "docs/" + nativeFile.getFileName().toString();

        Set<String> entries = listNliEntries(nliPath);
        assertTrue(
            entries.contains(expectedEntryName),
            "NLI ZIP should contain native file at subdirectory path '" + expectedEntryName + "', found: " + entries
        );
    }
}
