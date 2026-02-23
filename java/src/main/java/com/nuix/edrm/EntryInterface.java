package com.nuix.edrm;

import org.w3c.dom.Document;
import org.w3c.dom.Element;

import java.time.OffsetDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

public abstract class EntryInterface {
    protected final Map<String, EntryField> fields = new LinkedHashMap<>();

    public Iterable<String> getFields() { return fields.keySet(); }
    public EntryField getField(String fieldKey) {
        if (!fields.containsKey(fieldKey)) {
            throw new IllegalArgumentException("Field '" + fieldKey + "' does not exist on this entry.");
        }

        return fields.get(fieldKey);
    }
    public void putField(EntryField f) { fields.put(f.getName(), f); }
    public void setFieldValue(String fieldName, Object fieldValue) {
        if (fields.containsKey( fieldName)) {
            fields.get(fieldName).setValue(fieldValue);
        } else {
            throw new IllegalArgumentException("Field '" + fieldName + "' does not exist on this entry.");
        }
    }

    public abstract String getIdentifierField();
    public abstract String getName();
    public abstract String getTimeField();
    public abstract OffsetDateTime getItemDate();
    public abstract String getParentId();
    public String addAsParentPath(String existingPath) { return existingPath; }

    public abstract void addFile(Document document, Element container, Map<String, EntryInterface> entryMap, boolean forNli);
    public abstract void addLocationUri(Document document, Element container, Map<String, EntryInterface> entryMap, boolean forNli);
    public void addLocation(Document document, Element container, Map<String, EntryInterface> entryMap, boolean forNli) {
        Element locationList = document.createElement("Locations");
        container.appendChild(locationList);

        Element location = document.createElement("Location");
        locationList.appendChild(location);

        Element custodian = document.createElement("Custodian");
        custodian.appendChild(document.createTextNode(EDRMUtilities.EDRM_CONFIG.get("custodian")));
        location.appendChild(custodian);

        Element description = document.createElement("Description");
        description.appendChild(document.createTextNode(forNli ? "Location with Nuix case file." : "Location on disk."));
        location.appendChild(description);

        addLocationUri(document, location, entryMap, forNli);
    }
    public Element addDoc(Document document, Element container) {
        Element docElement = document.createElement("Document");
        docElement.setAttribute("DocID", this.fields.get(this.getIdentifierField()).getValue().toString());
        docElement.setAttribute("DocType", "File");
        docElement.setAttribute("MimeType", this.fields.get("MIME Type").getValue().toString());
        container.appendChild(docElement);

        return docElement;
    }

    public void serializeFieldDefinitions(Document document, Element fieldList) {
        for (Map.Entry<String, EntryField> entry : fields.entrySet()) {
            entry.getValue().serializeDefinition(document, fieldList);
        }
    }

    public void serializeFieldValues(Document document, Element values) {
        for (Map.Entry<String, EntryField> entry : fields.entrySet()) {
            entry.getValue().serializeValue(document, values);
        }
    }

    public void serializeEntry(Document document, Element container, Map<String, EntryInterface> entryMap, boolean forNli) {
        Element doc = addDoc(document, container);
        Element valueList = document.createElement("FieldValues");
        doc.appendChild(valueList);
        serializeFieldValues(document, valueList);

        addFile(document, doc, entryMap, forNli);
        addLocation(document, doc, entryMap, forNli);
    }
}
