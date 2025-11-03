package com.nuix.nli.edrm;

import org.w3c.dom.Document;
import org.w3c.dom.Element;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.FileOwnerAttributeView;
import java.nio.file.attribute.UserPrincipal;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Map;

public class FileEntry extends EntryInterface {
    protected final Path filePath;
    protected final String parentId;
    protected OffsetDateTime itemDate;

    public FileEntry(String filePath, String mimeType) { this(filePath, mimeType, null); }

    public FileEntry(String filePath, String mimeType, String parentId) {
        this.filePath = Paths.get(filePath).toAbsolutePath().normalize();
        this.parentId = parentId;

        fillBasicFields(mimeType);
        fillHashFields();
        putField(FieldFactory.generateField("File Size", EntryField.Type.LongInteger, this.filePath.toFile().length()));
    }

    private void fillBasicFields(String mimeType) {
        putField(FieldFactory.generateField("MIME Type", EntryField.Type.Text, mimeType));
        putField(FieldFactory.generateField("Name", EntryField.Type.Text, this.filePath.getFileName().toString()));

        try {
            BasicFileAttributes fileAttributes = Files.readAttributes(this.filePath, BasicFileAttributes.class);
            Instant lastModifiedTime = fileAttributes.lastModifiedTime().toInstant();
            Instant lastAccessedTime = fileAttributes.lastAccessTime().toInstant();
            Instant createdTime = fileAttributes.creationTime().toInstant();

            FileOwnerAttributeView ownerView = Files.getFileAttributeView(this.filePath, FileOwnerAttributeView.class);
            UserPrincipal owner = ownerView.getOwner();
            String ownerName = owner != null ? owner.getName() : "Undefined";

            this.itemDate = OffsetDateTime.ofInstant(lastModifiedTime, ZoneOffset.UTC);
            putField(FieldFactory.generateField("Item Date", EntryField.Type.DateTime, EDRMUtilities.formatDateTime(this.itemDate)));
            putField(FieldFactory.generateField("File Accessed", EntryField.Type.DateTime, EDRMUtilities.formatDateTime(OffsetDateTime.ofInstant(lastAccessedTime, ZoneOffset.UTC))));
            putField(FieldFactory.generateField("File Created", EntryField.Type.DateTime, EDRMUtilities.formatDateTime(OffsetDateTime.ofInstant(createdTime, ZoneOffset.UTC))));
            putField(FieldFactory.generateField("File Modified", EntryField.Type.DateTime, EDRMUtilities.formatDateTime(OffsetDateTime.ofInstant(lastModifiedTime, ZoneOffset.UTC))));
            putField(FieldFactory.generateField("File Owner", EntryField.Type.Text, ownerName));
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }

    protected void fillHashFields() {
        putField(FieldFactory.generateField("SHA-1", EntryField.Type.Text, EDRMUtilities.hashFile(this.filePath, "SHA-1").hashString()));
    }

    @Override public String getIdentifierField() { return "SHA-1"; }
    @Override public String getName() { return getField("Name").getValue().toString(); }
    @Override public String getTimeField() { return "Item Date"; }
    @Override public OffsetDateTime getItemDate() { return itemDate; }
    @Override public String getParentId() { return parentId; }

    public Path getFilePath() { return filePath; }

    protected String calculateMD5() { return EDRMUtilities.hashFile(filePath, "MD5").hashString(); }

    @Override public void addLocationUri(Document document, Element container, Map<String, EntryInterface> entryMap, boolean forNli) {
        Element locationUriElement = document.createElement("LocationURI");
        String locationUri = "";
        if (forNli) {
            locationUri = EDRMUtilities.generateRelativePath(this, entryMap);
            locationUri = URLEncoder.encode(locationUri, StandardCharsets.UTF_8)
                    .replace("+", "%20")
                    .replace("%2F", "/");
        } else {
            locationUri = filePath.toUri().toString();
        }
        locationUriElement.appendChild(document.createTextNode(locationUri));
        container.appendChild(locationUriElement);
    }

    @Override public void addFile(Document document, Element container, Map<String, EntryInterface> entryMap, boolean forNli) {
        Element fileList = document.createElement("Files");
        container.appendChild(fileList);

        Element fileElement = document.createElement("File");
        fileElement.setAttribute("FileType", "Native");
        fileList.appendChild(fileElement);

        Element externalFile = document.createElement("ExternalFile");
        fileElement.appendChild(externalFile);

        if (forNli) {
            Path relativePath;
            if (null == getParentId() || entryMap.get(getParentId()).getClass().isAssignableFrom(DirectoryEntry.class)) {
                relativePath = Path.of(EDRMUtilities.generateRelativePath(this, entryMap));
            } else {
                relativePath = Path.of("natives").resolve(getName());
            }

            Path filePath = relativePath.getParent() != null ? relativePath.getParent() : Path.of("");
            externalFile.setAttribute("FilePath", filePath.toString());
        } else {
            externalFile.setAttribute("FilePath", this.filePath.toString());
        }

        externalFile.setAttribute("FileName", filePath.getFileName().toString());
        externalFile.setAttribute("Hash", calculateMD5());
        externalFile.setAttribute("HashType", "MD5");
    }

}