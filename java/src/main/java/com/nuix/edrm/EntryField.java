package com.nuix.edrm;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

import java.time.OffsetDateTime;

public class EntryField {
    public enum Type {
        Text,
        DateTime,
        LongInteger,
        LongText,
        Decimal,
        Boolean
    }

    private final String key;
    private final String name;
    private final Type dataType;
    private Object value;

    public EntryField(String key, String name, Type dataType, Object defaultValue) {
        this.key = key;
        this.name = name;
        this.dataType = dataType;
        this.value = defaultValue;
    }

    public String getKey() { return key; }
    public String getName() { return name; }
    public Type getDataType() { return dataType; }
    public Object getValue() { return value; }
    public void setValue(Object value) { this.value = value; }

    public void serializeDefinition(Document document, Element fieldList) {
        // ensure only one definition per name
        for (int i = 0; i < fieldList.getChildNodes().getLength(); i++) {
            Node childNode = fieldList.getChildNodes().item(i);
            if (childNode instanceof Element e && name.equals(e.getAttribute("Name"))) return;
        }

        Element f = document.createElement("Field");
        f.setAttribute("Name", name);
        f.setAttribute("DataType", dataType.name());
        f.setAttribute("Key", key);
        fieldList.appendChild(f);
    }

    public void serializeValue(Document document, Element valueList) {
        Element v = document.createElement(key);

        String valueText;
        if (value == null) {
            valueText = "";
        } else if (value instanceof OffsetDateTime odt) {
            valueText = EDRMUtilities.formatDateTime(odt);
        } else if (value instanceof Double d) {
            valueText = String.format(java.util.Locale.ROOT, "%.4f", d);
        } else if (value instanceof Float f) {
            valueText = String.format(java.util.Locale.ROOT, "%.4f", f);
        } else {
            valueText = EDRMUtilities.sanitizeXml(String.valueOf(value));
        }

        v.appendChild(document.createTextNode(valueText));
        valueList.appendChild(v);
    }
}