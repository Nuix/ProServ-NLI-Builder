package com.nuix.nli.edrm;

import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

import org.w3c.dom.Document;
import org.w3c.dom.Element;

public class DirectoryEntry extends FileEntry {
    private final Path directory;

    public DirectoryEntry(String directoryPath) { this(directoryPath, null); }

    public DirectoryEntry(String directoryPath, String parentId) {
        super(directoryPath, "filesystem/directory", parentId);
        this.directory = Paths.get(directoryPath);
    }

    @Override protected void fillHashFields() {
        setFieldValue("SHA-1", EDRMUtilities.hashDirectory(this.directory, "SHA-1").hashString());
    }

    public Path getDirectory() { return directory; }

    @Override public String addAsParentPath(String existingPath) {
        try {
            return URLEncoder.encode(this.getName(), EDRMUtilities.EDRM_CONFIG
                    .getOrDefault("encoding", StandardCharsets.UTF_8.name())) + "/" + existingPath;
        } catch (UnsupportedEncodingException e) {
            throw new RuntimeException(e);
        }
    }

    @Override public void addFile(Document document, Element container, Map<String, EntryInterface> entryMap, boolean forNli) {
        return;
    }

    @Override protected String calculateMD5() {
        return EDRMUtilities.hashDirectory(this.directory, "MD5").hashString();
    }
}