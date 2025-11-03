package com.nuix.nli.edrm;

import org.w3c.dom.Document;
import org.w3c.dom.Element;

import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

public class EDRMBuilder {
    private final Map<String, EntryInterface> entryMap = new LinkedHashMap<>();
    private final Map<String, List<String>> familyMap = new LinkedHashMap<>();
    private final EntryInterface EMPTY = new MappingEntry(Map.of(), "application/x-empty");

    private boolean asNli = false;
    private Path outputPath = Path.of(".", "output.xml").normalize().toAbsolutePath();

    public boolean isAsNli() { return asNli; }
    public void setAsNli(boolean asNli) { this.asNli = asNli; }

    public Path getOutputPath() { return outputPath; }
    public void setOutputPath(Path outputPath) { this.outputPath = outputPath; }

    public Map<String, EntryInterface> getEntryMap() { return new LinkedHashMap<>(entryMap); }

    public String addEntry(EntryInterface entry) {
        String id = entry.getField(entry.getIdentifierField()).getValue().toString();
        entryMap.put(id, entry);

        String parentId = entry.getParentId();
        if (!familyMap.containsKey(id))
            familyMap.put(id, new LinkedList<String>());

        if (null != parentId && !parentId.isEmpty()) {
            List<String> family = familyMap.getOrDefault(parentId, new LinkedList<>());
            family.add(id);
            familyMap.put(parentId, family);
        }

        return id;
    }

    public EntryInterface getEntry(String id) {
        if (null == id || !entryMap.containsKey(id)) return EMPTY;
        return entryMap.get(id);
    }

    public String addFile(String filePath, String mimetype) { return addFile(filePath, mimetype, null); }
    public String addFile(String filePath, String mimetype, String parentId) {
        return addEntry(new FileEntry(filePath, mimetype, parentId));
    }

    public String addDirectory(String directory) { return addDirectory(directory, null); }
    public String addDirectory(String directory, String parentId) {
        return addEntry(new DirectoryEntry(directory, parentId));
    }

    public String addMapping(Map<String, Object> mapping, String mimetype) { return addMapping(mapping, mimetype, null); }
    public String addMapping(Map<String, Object> mapping, String mimetype, String parentId) {
        return addEntry(new MappingEntry(mapping, mimetype, parentId));
    }

    private void addFolder(String docId, Document document, Element container, Map<String, List<String>> familyMap) {
        EntryInterface docEntry = getEntry(docId);
        if (null != docEntry.getParentId()) {
            Element docElement = document.createElement("Document");
            docElement.setAttribute("DocId", docId);
            container.appendChild(docElement);
        }

        if (!familyMap.containsKey(docId)) {
            return;
        }

        List<String> family = familyMap.remove(docId);
        if(!family.isEmpty()) {
            Element folderElement = document.createElement("Folder");
            folderElement.setAttribute("DocId", docId);
            container.appendChild(folderElement);
            for (String childId : this.familyMap.get(docId)) {
                addFolder(childId, document, folderElement, familyMap);
            }
        }
    }

    public Document build() {
        try {
            Document doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().newDocument();
            Element root = doc.createElement("Root");
            doc.appendChild(root);
            root.setAttribute("MajorVersion", "1");
            root.setAttribute("MinorVersion", "2");
            root.setAttribute("Description", "EDRM XML Load File");
            root.setAttribute("Locale", "US");
            root.setAttribute("DataInterchangeType", "Update");

            Element fields = doc.createElement("Fields");
            root.appendChild(fields);

            for (EntryInterface e : entryMap.values()) {
                e.serializeFieldDefinitions(doc, fields);
            }

            Element batch = doc.createElement("Batch");
            root.appendChild(batch);
            Element documentsList = doc.createElement("Documents");
            batch.appendChild(documentsList);

            for (Map.Entry<String, EntryInterface> entry : entryMap.entrySet()) {
                entry.getValue().serializeEntry(doc, documentsList, entryMap, asNli);
            }

            Element relationships = doc.createElement("Relationships");
            batch.appendChild(relationships);
            for (Map.Entry<String, List<String>> entry : familyMap.entrySet()) {
                String parentId = entry.getKey();
                List<String> family = entry.getValue();

                for (String childId : family) {
                    Element relationship = doc.createElement("Relationship");
                    relationship.setAttribute("ParentDocId", parentId);
                    relationship.setAttribute("ChildDocId", childId);
                    relationship.setAttribute("RelationshipType", "Container");
                    relationships.appendChild(relationship);
                }
            }

            Element foldersList = doc.createElement("Folders");
            batch.appendChild(foldersList);

            LinkedHashMap<String, List<String>> familyMapCopy = new LinkedHashMap<>(familyMap);
            for (String entryID : familyMap.keySet()) {
                if (familyMapCopy.containsKey(entryID)) {
                    addFolder(entryID, doc, foldersList, familyMapCopy);
                }
            }

            return doc;
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    public void save(Document doc) {
        if (null == outputPath) throw new IllegalStateException("outputPath not set");

        if (null == doc) {
            doc = build();
        }

        try {
            Files.createDirectories(outputPath.getParent());
            Transformer t = TransformerFactory.newInstance().newTransformer();
            t.setOutputProperty(OutputKeys.INDENT, "yes");
            t.setOutputProperty(OutputKeys.METHOD, "xml");
            t.setOutputProperty(OutputKeys.ENCODING, EDRMUtilities.EDRM_CONFIG.getOrDefault("encoding", "UTF-8"));
            t.setOutputProperty("{http://xml.apache.org/xslt}indent-amount", "2");
            t.transform(new DOMSource(doc), new StreamResult(outputPath.toFile()));
        } catch (IOException | javax.xml.transform.TransformerException e) {
            throw new RuntimeException(e);
        }
    }

    public void save() {
        save(null);
    }
}