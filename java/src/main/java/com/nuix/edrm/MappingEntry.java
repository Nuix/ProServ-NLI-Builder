package com.nuix.edrm;

import org.w3c.dom.Document;
import org.w3c.dom.Element;

import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.OffsetDateTime;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;

public class MappingEntry extends EntryInterface {
    protected final Map<String, Object> data = new LinkedHashMap<>();
    protected final String parentId;
    protected final String mimeType;

    public MappingEntry(Map<String, Object> mapping, String mimeType) { this(mapping, mimeType, null); }

    public MappingEntry(Map<String, Object> mapping, String mimeType, String parentId) {
        this.parentId = parentId;
        this.mimeType = mimeType;

        Map<String, Object> newData = mapping != null ? mapping : Map.of();
        this.data.putAll(newData);

        fillInitialFields(newData);
        fillGenericFields(mimeType);
    }

    private void fillInitialFields(Map<String, Object> mapping) {
        mapping.forEach((k,v) -> {
            EntryField.Type data_type;
            Object value = v;
            if (v instanceof Boolean) {
                data_type = EntryField.Type.Boolean;
            } else if (v instanceof Short || v instanceof Integer || v instanceof Long) {
                data_type = EntryField.Type.LongInteger;
            } else if (v instanceof Float || v instanceof Double) {
                data_type = EntryField.Type.Decimal;
            } else if (v instanceof OffsetDateTime || v instanceof java.util.Date || v instanceof java.time.LocalDateTime
                    || v instanceof java.time.ZonedDateTime || v instanceof java.time.Instant) {
                data_type = EntryField.Type.DateTime;
            } else {
                data_type = EntryField.Type.Text;
                value = v.toString();
            }

            String key_name = k.trim();
            if (key_name.isEmpty()) {
                int i = 1;
                String placeholder = "key_"+i;
                while (this.fields.containsKey(placeholder)) {
                    placeholder = "key_"+(++i);
                }
                key_name = placeholder;
            }
            putField(FieldFactory.generateField(key_name, data_type, value));
        });
    }

    private void fillGenericFields(String mimeType) {
        putField(FieldFactory.generateField("MIME Type", EntryField.Type.Text, mimeType));
        putField(FieldFactory.generateField("Name", EntryField.Type.Text, getBaseName()));
        
        Map<String, Object> dataCopy = new LinkedHashMap<>(this.data);
        dataCopy.put("name", getBaseName());
        String hashedData = EDRMUtilities.hash_data(dataCopy, "SHA-1");
        putField(FieldFactory.generateField("SHA-1", EntryField.Type.Text, hashedData));
        putField(FieldFactory.generateField("Item Date", EntryField.Type.DateTime, OffsetDateTime.now()));
    }

    public Map<String, Object> getData() {
        return data;
    }

    public String getName() {
        return EDRMUtilities.sanitizeXml(EDRMUtilities.sanitizeFilename( getBaseName()));
    }

    public String getBaseName() {
        String default_rowname_field = EDRMUtilities.EDRM_CONFIG.getOrDefault("default_rowname_field", "Name");
        String name = "";
        if (this.data.containsKey(default_rowname_field)) {
            name = this.data.getOrDefault(default_rowname_field, "").toString();
        } else {
            String nameField = this.data.keySet().stream().filter(k -> k.toLowerCase().contains("name")).findFirst().orElse("");
            if (!nameField.isEmpty()) {
                name = this.data.getOrDefault(nameField, "").toString();
            }
        }

        if (name.isEmpty()) {
            String firstField = this.data.keySet().stream().findFirst().orElse("");
            if (!firstField.isEmpty()) {
                name = this.data.getOrDefault(firstField, "").toString();
            } else {
                name = "MappingEntry";
            }
        }

        return name;
    }

    public String getText() {
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, EntryField> entry : fields.entrySet()) {
            if (!sb.isEmpty()) sb.append("\n");
            sb.append(entry.getKey()).append("=").append(entry.getValue().getValue());
        }
        return sb.toString();
    }

    @Override public String getIdentifierField() { return "SHA-1"; }

    @Override public String getTimeField() {
        if (this.data.containsKey(EDRMUtilities.EDRM_CONFIG.getOrDefault("default_itemdate_field", "Item Date"))) {
            return EDRMUtilities.EDRM_CONFIG.getOrDefault("default_itemdate_field", "Item Date");
        }

        String timeField = this.data.keySet().stream().filter(k -> k.toLowerCase().contains("time")).findFirst().orElse("");
        if (!timeField.isEmpty()) {
            return timeField;
        }

        String dateField = this.data.keySet().stream().filter(k -> k.toLowerCase().contains("date")).findFirst().orElse("");
        if (!dateField.isEmpty()) {
            return dateField;
        }

        return null;
    }

    @Override public OffsetDateTime getItemDate() {
        String timeField = this.getTimeField();
        if (null == timeField) return OffsetDateTime.now();

        Object timeValue = this.data.get(timeField);
        if (null == timeValue) return OffsetDateTime.now();
        if (timeValue instanceof String && timeValue.toString().isEmpty()) return OffsetDateTime.now();

        if (timeValue instanceof OffsetDateTime) return (OffsetDateTime)timeValue;
        if (timeValue instanceof java.util.Date) return ((java.util.Date)timeValue).toInstant().atOffset(java.time.ZoneOffset.UTC);
        if (timeValue instanceof java.time.LocalDateTime) return ((java.time.LocalDateTime)timeValue).atOffset(java.time.ZoneOffset.UTC);
        if (timeValue instanceof java.time.ZonedDateTime) return ((java.time.ZonedDateTime)timeValue).toOffsetDateTime();
        if (timeValue instanceof java.time.Instant) return ((java.time.Instant)timeValue).atOffset(java.time.ZoneOffset.UTC);

        if (timeValue instanceof String) {
            try {
                return OffsetDateTime.parse((String)timeValue);
            } catch (Exception e) {
                return OffsetDateTime.now();
            }
        } else {
            return OffsetDateTime.now();
        }
    }

    @Override public String getParentId() { return parentId; }

    @Override public String addAsParentPath(String existingPath) {
        try {
            return URLEncoder.encode(getName(), EDRMUtilities.EDRM_CONFIG
                    .getOrDefault("encoding", StandardCharsets.UTF_8.name())) + "/" + existingPath;
        } catch (UnsupportedEncodingException e) {
            throw new RuntimeException(e);
        }
    }

    @Override public void addLocationUri(
            Document document,
            Element container,
            Map<String, EntryInterface> entryMap,
            boolean forNli) {

        if (forNli) {
            Element locationUriElement = document.createElement("LocationURI");
            String locationUri = EDRMUtilities.generateRelativePath(this, entryMap);
            locationUri = URLEncoder.encode(locationUri, StandardCharsets.UTF_8)
                    .replace("+", "%20")
                    .replace("%2F", "/");
            locationUriElement.appendChild(document.createTextNode(locationUri));
            container.appendChild(locationUriElement);
        }
    }

    void serializeFileContent(Document document, Element container, java.util.Map<String, EntryInterface> entryMap) {
        Element externalFile = document.createElement("ExternalFile");
        container.appendChild(externalFile);
        externalFile.setAttribute("FilePath", "natives");
        externalFile.setAttribute("FileName", this.fields.get(this.getIdentifierField()).getValue().toString());

        String md5 = calculateMD5();
        externalFile.setAttribute("Hash", md5);
        externalFile.setAttribute("HashType", "MD5");
    }

    String calculateMD5() {
        try {
            MessageDigest md = MessageDigest.getInstance("MD5");
            md.update(this.getText().getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(md.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    @Override public void addFile(Document document, Element container, java.util.Map<String, EntryInterface> entryMap, boolean forNli) {
        String text = this.getText();
        if (null == text || text.isEmpty()) return;

        Element filesList = document.createElement("Files");
        container.appendChild(filesList);

        Element file = document.createElement("File");
        file.setAttribute("FileType", forNli ? "Native" : "Text");
        filesList.appendChild(file);

        if(forNli) {
            serializeFileContent(document, file, entryMap);
        } else {
            Element inlineContent = document.createElement("InlineContent");
            inlineContent.appendChild(document.createTextNode(text));
            file.appendChild(inlineContent);
        }
    }
}