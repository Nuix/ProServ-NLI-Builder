package com.nuix.nli.nli;

import com.nuix.nli.edrm.*;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.*;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import java.util.Properties;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public class NLIGenerator {
    private static final boolean IS_WINDOWS = System.getProperty("os.name").toLowerCase().contains("win");

    private static Map<String, String> loadNLIConfig() {
        Properties props = new Properties();
        try (InputStream input = NLIGenerator.class.getResourceAsStream("/nli.config")) {
            if (input == null) {
                throw new RuntimeException("Could not find nli.config in resources");
            }
            props.load(input);
            return props.entrySet().stream()
                    .collect(Collectors.toMap(
                            e -> String.valueOf(e.getKey()),
                            e -> String.valueOf(e.getValue())
                    ));
        } catch (IOException e) {
            throw new RuntimeException("Failed to load nli.config", e);
        }
    }
    public static final Map<String,String> NLI_CONFIG = loadNLIConfig();

    private final EDRMBuilder builder = new EDRMBuilder();

    public NLIGenerator() {
        builder.setAsNli(true);
    }

    public String addEntry(EntryInterface entry) {
        if (entry instanceof CompoundEnty ce) {
            return ce.addToBuilder(builder);
        } else {
            return builder.addEntry(entry);
        }
    }
    public EntryInterface getEntry(String id) {
        return builder.getEntry(id);
    }

    public String addFile(String filePath, String mimeType, String parentId) { return builder.addFile(filePath, mimeType, parentId); }
    public String addDirectory(String directoryPath, String parentId) { return builder.addDirectory(directoryPath, parentId); }
    public String addMapping(Map<String, Object> mapping, String mimeType, String parentId) { return builder.addMapping(mapping, mimeType, parentId); }

    private void generateMetadataFile(Path metadataPath) {
        try {
            Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument();
            Element root = doc.createElement("image-metadata");
            doc.appendChild(root);

            Element properties = doc.createElement("properties");
            root.appendChild(properties);

            Element caseElement = doc.createElement("property");
            caseElement.setAttribute("key", "case-number");
            caseElement.setAttribute("value", "01");
            properties.appendChild(caseElement);

            Element dateTimeElement = doc.createElement("property");
            dateTimeElement.setAttribute("key", "creation-datetime");
            dateTimeElement.setAttribute("value", OffsetDateTime.now().format(DateTimeFormatter.ofPattern(EDRMUtilities.EDRM_CONFIG.getOrDefault("date_time_format", "yyyy-MM-dd'T'HH:mm:ss.SSS"))) + " UTC");
            properties.appendChild(dateTimeElement);

            Element softwareElement = doc.createElement("property");
            softwareElement.setAttribute("key", "creation-software-name");
            softwareElement.setAttribute("value", "Nuix NLI Builder");

            Element evidenceElement = doc.createElement("property");
            evidenceElement.setAttribute("key", "evidence-number");
            evidenceElement.setAttribute("value", "01");
            properties.appendChild(evidenceElement);

            Element examinerElement = doc.createElement("property");
            examinerElement.setAttribute("key", "examiner-name");
            examinerElement.setAttribute("value", "Unknown");
            properties.appendChild(examinerElement);

            Path outputPath = metadataPath.resolve("image_metadata.xml");
            Files.createDirectories(outputPath.getParent());
            Transformer t = TransformerFactory.newInstance().newTransformer();
            t.setOutputProperty(OutputKeys.INDENT, "yes");
            t.setOutputProperty(OutputKeys.METHOD, "xml");
            t.setOutputProperty(OutputKeys.ENCODING, EDRMUtilities.EDRM_CONFIG.getOrDefault("encoding", "UTF-8"));
            t.setOutputProperty("{http://xml.apache.org/xslt}indent-amount", "2");
            t.transform(new DOMSource(doc), new StreamResult(outputPath.toFile()));
        } catch (ParserConfigurationException | IOException | javax.xml.transform.TransformerException e) {
            throw new RuntimeException(e);
        }
    }

    public void save(Path nliPath) {
        boolean doDelete = !Boolean.parseBoolean(NLI_CONFIG.getOrDefault("debug", "false"));

        try {
            Path temp = Files.createTempDirectory("nli_gen");
            try {
                Path buildPath = temp.resolve("NLI_Gen");
                Path metadataPath = buildPath.resolve("._metadata");
                Files.createDirectories(metadataPath);

                // Save EDRM XML
                Path edrmXml = metadataPath.resolve("image_contents.xml");
                builder.setOutputPath(edrmXml);
                builder.save();

                Map<String, EntryInterface> entryMap = builder.getEntryMap();
                for (EntryInterface entry : entryMap.values()) {
                    if (entry instanceof FileEntry fe) {
                        String relativePath;
                        if (null == fe.getParentId()) {
                            relativePath = fe.getFilePath().getFileName().toString();
                        } else if (entryMap.get(fe.getParentId()) instanceof DirectoryEntry de) {
                            relativePath = EDRMUtilities.generateRelativePath(de, entryMap);
                            relativePath = relativePath + "/" + fe.getFilePath().getFileName().toString();
                        } else {
                            relativePath = Path.of("natives", fe.getFilePath().getFileName().toString()).toString();
                        }

                        Path destinationPath = buildPath.resolve(relativePath);
                        if (null != destinationPath.getParent()) {
                            Files.createDirectories(destinationPath.getParent());
                        }

                        if (fe instanceof DirectoryEntry de) {
                            Files.createDirectories(destinationPath);
                        } else {
                            Files.copy(fe.getFilePath(), destinationPath, StandardCopyOption.REPLACE_EXISTING);
                        }
                    } else if (entry instanceof MappingEntry me) {
                        Path mappingPath;
                        if (null != me.getText()) {
                            mappingPath = buildPath.resolve("natives").resolve(me.getField(me.getIdentifierField()).getValue().toString());
                            mappingPath = mappingPath.normalize().toAbsolutePath();
                            Files.createDirectories(mappingPath.getParent());
                            if (IS_WINDOWS) {
                                mappingPath = Path.of("\\\\?\\" + mappingPath.toString());
                            }
                            Files.writeString(mappingPath, me.getText(),
                                    java.nio.charset.Charset.forName(EDRMUtilities.EDRM_CONFIG.getOrDefault("encoding", "UTF-8")));
                        }
                    }
                }

                generateMetadataFile(metadataPath);

                byte[] metadataHash = EDRMUtilities.hashFile(builder.getOutputPath(), "SHA-1").hashBytes();
                Path metadataHashPath = metadataPath.resolve("image_contents.sha1_hash");
                Files.write(metadataHashPath, metadataHash);

                // Zip the contents
                Path zipPath = temp.resolve(NLIUtilities.getFileNameWithoutExtension(nliPath) + ".zip");
                try (ZipOutputStream zos = new ZipOutputStream(Files.newOutputStream(zipPath))) {
                    try(Stream<Path> walked = Files.walk(buildPath)) {
                        walked.filter(Files::isRegularFile).forEach(p -> {
                            try {
                                String entryName = buildPath.relativize(p).toString().replace('\\', '/');
                                zos.putNextEntry(new ZipEntry(entryName));
                                Files.copy(p, zos);
                                zos.closeEntry();
                            } catch (IOException e) { throw new RuntimeException(e); }
                        });
                    }
                }

                Files.copy(zipPath, nliPath, StandardCopyOption.REPLACE_EXISTING);
            } finally {
                if (doDelete) {
                    try {
                        NLIUtilities.deleteRecursively(temp);
                    } catch (IOException e) {
                        // Ignore delete exceptions
                    }
                }
            }
        } catch (IOException e) {
            throw new RuntimeException(e);
        }
    }
}