package com.nuix.nli.edrm;

import java.io.IOException;
import java.io.InputStream;
import java.io.UnsupportedEncodingException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.stream.Collectors;
import java.util.regex.Pattern;

public class EDRMUtilities {
    public static record HashResult(String hashString, byte[] hashBytes) {}

    private static Map<String, String> loadEDRMConfig() {
        Properties props = new Properties();
        try (InputStream input = EDRMUtilities.class.getResourceAsStream("/edrm.config")) {
            if (input == null) {
                throw new RuntimeException("Could not find edrm.config in resources");
            }
            props.load(input);
            return props.entrySet().stream()
                    .collect(Collectors.toMap(
                            e -> String.valueOf(e.getKey()),
                            e -> String.valueOf(e.getValue())
                    ));
        } catch (IOException e) {
            throw new RuntimeException("Failed to load edrm.config", e);
        }
    }
    public static final Map<String,String> EDRM_CONFIG = loadEDRMConfig();

    public static final int HASH_BUFFER_SIZE = Integer.parseInt(EDRM_CONFIG.getOrDefault("hash_buffer_size", "" + (1024 * 1024) /* 1MB */));
    public static final DateTimeFormatter DATE_TIME_FORMAT = DateTimeFormatter.ofPattern(EDRM_CONFIG.getOrDefault("date_time_format", "yyyy-MM-dd'T'HH:mm:ss.SSS"));

    public static String formatDateTime(OffsetDateTime odt) {
        return DATE_TIME_FORMAT.format(odt.atZoneSameInstant(ZoneOffset.UTC)) + EDRMUtilities.EDRM_CONFIG.getOrDefault("time_zone_format", "+00:00");
    }

    public static String formatTimestamp(double epochSeconds) {
        return formatDateTime(OffsetDateTime.ofInstant(Instant.ofEpochMilli((long)(epochSeconds * 1000)), ZoneOffset.UTC));
    }


    public static String hash_data(Object data, String algorithm) {
        try {
            MessageDigest digester = MessageDigest.getInstance(algorithm);
            digester.reset();
            digester.update(data.toString().getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digester.digest());
        } catch (NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    public static HashResult hashFile(Path file, String algorithm) {
        if(file.toFile().isDirectory()) {
            return new HashResult("", new byte[0]);
        }

        try (InputStream in = Files.newInputStream(file); DigestInputStream dis = new DigestInputStream(in, MessageDigest.getInstance(algorithm))) {
            byte[] buffer = new byte[HASH_BUFFER_SIZE];
            while (dis.read(buffer) != -1) { /* streaming */ }
            byte[] digest = dis.getMessageDigest().digest();
            return new HashResult(HexFormat.of().formatHex(digest), digest);
        } catch (IOException | NoSuchAlgorithmException e) {
            throw new RuntimeException(e);
        }
    }

    public static HashResult hashDirectory(Path dir, String algorithm) {
        try {
            MessageDigest md = MessageDigest.getInstance(algorithm);
            if (Files.isDirectory(dir)) {
                try (var walk = Files.walk(dir)) {
                    walk.filter(Files::isRegularFile).sorted().forEach(p -> {
                        md.update(p.getFileName().toString().getBytes(StandardCharsets.UTF_8));
                        try (InputStream in = Files.newInputStream(p)) {
                            byte[] buffer = new byte[HASH_BUFFER_SIZE];
                            int r;
                            while ((r = in.read(buffer)) != -1) {
                                md.update(buffer, 0, r);
                            }
                        } catch (IOException ex) {
                            throw new RuntimeException(ex);
                        }
                    });
                }
            }
            byte[] digest = md.digest();
            return new HashResult(HexFormat.of().formatHex(digest), digest);
        } catch (NoSuchAlgorithmException | IOException e) {
            throw new RuntimeException(e);
        }
    }

    private static final Pattern XML_ILLEGAL;
    static {
        List<String[]> ILLEGAL_UNI_CHARS = List.of(
                new String[]{"\u0000", "\u0008"},
                new String[]{"\u000B", "\u000C"},
                new String[]{"\u000E", "\u001F"},
                new String[]{"\u007F", "\u0084"},
                new String[]{"\u0086", "\u009F"},
                new String[]{"\uFDD0", "\uFDDF"},
                new String[]{"\uFFFE", "\uFFFF"},
                new String[]{"\uD83F\uDFFE", "\uD83F\uDFFF"},
                new String[]{"\uD87F\uDFFE", "\uD87F\uDFFF"},
                new String[]{"\uD8BF\uDFFE", "\uD8BF\uDFFF"},
                new String[]{"\uD8FF\uDFFE", "\uD8FF\uDFFF"},
                new String[]{"\uD93F\uDFFE", "\uD93F\uDFFF"},
                new String[]{"\uD97F\uDFFE", "\uD97F\uDFFF"},
                new String[]{"\uD9BF\uDFFE", "\uD9BF\uDFFF"},
                new String[]{"\uD9FF\uDFFE", "\uD9FF\uDFFF"},
                new String[]{"\uDA3F\uDFFE", "\uDA3F\uDFFF"},
                new String[]{"\uDA7F\uDFFE", "\uDA7F\uDFFF"},
                new String[]{"\uDABF\uDFFE", "\uDABF\uDFFF"},
                new String[]{"\uDAFF\uDFFE", "\uDAFF\uDFFF"},
                new String[]{"\uDB3F\uDFFE", "\uDB3F\uDFFF"},
                new String[]{"\uDB7F\uDFFE", "\uDB7F\uDFFF"},
                new String[]{"\uDBBF\uDFFE", "\uDBBF\uDFFF"},
                new String[]{"\uDBFF\uDFFE", "\uDBFF\uDFFF"}
        );
        String ILLEGAL_UNI_CHARS_REGEX ="[" + ILLEGAL_UNI_CHARS.stream()
                                                               .map(c -> c[0] + "-" + c[1])
                                                               .reduce("", (a,b) -> a + "," + b) + "]";
        XML_ILLEGAL= Pattern.compile(ILLEGAL_UNI_CHARS_REGEX);
    }

    public static String sanitizeXml(String s) {
        return XML_ILLEGAL.matcher(s).replaceAll("_");
    }

    private static final Pattern FILE_INVALID = Pattern.compile("[<>:\"/|?*\\\\]|[\u0000-\u001F\u007F]");

    public static String sanitizeFilename(String filename) {
        String out = FILE_INVALID.matcher(filename).replaceAll("_").trim();
        if (out.endsWith(".")) out = out.substring(0, out.length()-1);
        return out;
    }

    public static String generateRelativePath(EntryInterface entry, Map<String, EntryInterface> entryMap) {
        String relativePath = null;
        try {
            relativePath = URLEncoder.encode(entry.getName(), EDRMUtilities.EDRM_CONFIG.getOrDefault("encoding", StandardCharsets.UTF_8.name()));
        } catch (UnsupportedEncodingException e) {
            throw new RuntimeException(e);
        }

        EntryInterface tmpCurrentEntry = entry;
        while (tmpCurrentEntry.getParentId() != null) {
            tmpCurrentEntry = entryMap.get(tmpCurrentEntry.getParentId());
            relativePath = tmpCurrentEntry.addAsParentPath(relativePath);
        }

        return relativePath;
    }
}