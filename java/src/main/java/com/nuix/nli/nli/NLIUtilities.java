package com.nuix.nli.nli;

import java.io.IOException;
import java.nio.file.FileVisitResult;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.SimpleFileVisitor;

public class NLIUtilities {
    public static void deleteRecursively(Path path) throws IOException {
        if (!Files.exists(path)) return;

        Files.walkFileTree(path, new SimpleFileVisitor<Path>() {
            public FileVisitResult visitFile(Path file, java.nio.file.attribute.BasicFileAttributes attrs) throws java.io.IOException {
                Files.delete(file);
                return FileVisitResult.CONTINUE;
            }

            public FileVisitResult postVisitDirectory(Path dir, java.io.IOException exc) throws java.io.IOException {
                Files.delete(dir);
                return FileVisitResult.CONTINUE;
            }
        });
    }

    public static String getFileNameWithoutExtension(Path path) {
        if (path == null) {
            return "";
        }

        Path fileName = path.getFileName();
        if (fileName == null) {
            return "";
        }

        String fileNameStr = fileName.toString();

        // Handle edge cases
        if (fileNameStr.isEmpty() || fileNameStr.equals(".") || fileNameStr.equals("..")) {
            return "";
        }

        // Find last dot, but ignore if it's the first character (hidden files)
        int lastDotIndex = fileNameStr.lastIndexOf('.');

        if (lastDotIndex > 0) {
            return fileNameStr.substring(0, lastDotIndex);
        }

        return fileNameStr;  // No extension or starts with dot
    }
}
