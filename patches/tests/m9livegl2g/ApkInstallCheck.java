import com.android.apksig.ApkVerifier;
import com.android.apksig.internal.apk.AndroidBinXmlParser;
import java.io.File;
import java.nio.ByteBuffer;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.Map;
import java.util.zip.ZipFile;

/** Validate the built APK, not only Gradle source or its cryptographic signature. */
public final class ApkInstallCheck {
    private static final String CERTIFICATE_SHA256 =
            "255cb09eaddd26a9cc680786e4985372cf24d0e54bb120fc44d48f3273ff3956";

    private static void require(boolean ok, String message) {
        if (!ok) throw new IllegalStateException(message);
    }

    public static void main(String[] args) throws Exception {
        require(args.length == 2, "Usage: ApkInstallCheck APK expectedVersionName");
        Map<String, String> manifest = new HashMap<>();
        try (ZipFile zip = new ZipFile(args[0])) {
            var parser = new AndroidBinXmlParser(ByteBuffer.wrap(
                    zip.getInputStream(zip.getEntry("AndroidManifest.xml")).readAllBytes()));
            while (parser.next() != AndroidBinXmlParser.EVENT_END_DOCUMENT) {
                if (parser.getEventType() != AndroidBinXmlParser.EVENT_START_ELEMENT) continue;
                String tag = parser.getName();
                if (!tag.equals("manifest") && !tag.equals("uses-sdk")) continue;
                for (int i = 0; i < parser.getAttributeCount(); i++) {
                    int type = parser.getAttributeValueType(i);
                    if (type == AndroidBinXmlParser.VALUE_TYPE_STRING) {
                        manifest.put(parser.getAttributeName(i), parser.getAttributeStringValue(i));
                    } else if (type == AndroidBinXmlParser.VALUE_TYPE_INT) {
                        manifest.put(parser.getAttributeName(i), "" + parser.getAttributeIntValue(i));
                    }
                }
            }
            require(zip.getEntry("lib/arm64-v8a/libm9color.so") != null, "Missing arm64 renderer");
        }
        String name = manifest.get("versionName");
        require(name != null && !name.isEmpty(), "Missing versionName");
        // AOSP android.content.res.Element: MAX_ATTR_LEN_NAME and AndroidManifest_versionName.
        require(name.length() <= 1024,
                "Android rejects versionName length " + name.length() + " > 1024");
        // Keep project labels short; history belongs in Git and the handoff.
        require(name.length() <= 64, "Project versionName must stay within 64 characters");
        require(name.equals(args[1]), "Unexpected versionName: " + name);
        require("com.m9project.m9cam.photon".equals(manifest.get("package")), "Wrong package");
        require("26".equals(manifest.get("minSdkVersion")), "Unexpected minimum SDK");
        require("35".equals(manifest.get("targetSdkVersion")), "Unexpected target SDK");
        require(Integer.parseInt(manifest.get("versionCode")) >= 26681, "Version downgrade");
        require(!manifest.containsKey("split"), "Expected standalone APK");
        var result = new ApkVerifier.Builder(new File(args[0])).build().verify();
        require(result.isVerified(), "APK signature verification failed: " + result.getErrors());
        require(result.getSignerCertificates().size() == 1, "Unexpected signer count");
        String signer = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(result.getSignerCertificates().get(0).getEncoded()));
        require(CERTIFICATE_SHA256.equals(signer), "Update signing certificate changed");
        System.out.println("APK INSTALL CHECK PASS: package=" + manifest.get("package")
                + " versionName=" + name + " length=" + name.length()
                + " versionCode=" + manifest.get("versionCode")
                + " minSdk=" + manifest.get("minSdkVersion")
                + " targetSdk=" + manifest.get("targetSdkVersion")
                + " signerSHA256=" + signer);
    }
}
