---
name: app-store
description: Apple App Store and Google Play Store publishing, App Store Optimization (ASO), metadata authoring, screenshot & preview asset generation, App Store Connect API automation, and Apple Review Guideline compliance checks.
metadata:
  version: 1.0.0
---

# App Store & ASO Excellence

`app-store` is a specialized skill for crafting high-converting mobile store listings, automating App Store Connect / Google Play Console workflows, and ensuring zero-rejection store submissions.

## Core Capabilities

### 1. App Store Optimization (ASO)
- **Title (30 chars)**: Brand name + high-volume primary keyword.
- **Subtitle (30 chars)**: Engaging value proposition with secondary keywords.
- **Keyword Field (100 chars)**: Comma-separated without spaces, no repeated words, singular forms only.
- **Promotional Text (170 chars)**: Dynamic updates without needing a new binary release.
- **Full Description (4,000 chars)**: Hook in first 3 lines, feature bullet points, social proof, and localized CTA.

### 2. Store Assets & Screenshot Blueprint
- **Display Resolutions**:
  - iPhone 6.9" (1320 x 2868 px)
  - iPhone 6.7" (1290 x 2796 px)
  - iPhone 6.5" (1242 x 2688 px)
  - iPad Pro 13" (2064 x 2752 px)
- **Visual Composition**:
  - Slide 1: Core value proposition + hero product mockup.
  - Slide 2: Primary feature in action with bold, readable headline.
  - Slide 3: Interactive workflow or social validation.
  - Slide 4-5: Detailed power features and dark mode preview.

### 3. Apple Review Compliance Check (Prevent Rejections)
- **Guideline 2.1 (Performance)**: Verify no placeholder text, test credentials supplied in review notes, and zero crash logs on launch.
- **Guideline 3.1.1 (In-App Purchase)**: Ensure digital content uses StoreKit; physical goods use external payment.
- **Guideline 4.0 (Design)**: Ensure clean navigation, compliance with Apple Human Interface Guidelines (HIG), and iPad multitasking support.
- **Guideline 5.1 (Privacy)**: Accurate App Privacy Nutrition Labels, working Privacy Policy URL, and justification for requested permissions (Camera, Location, Tracking).

### 4. App Store Connect Automation (CLI)
```bash
# Upload build with xcrun
xcrun altool --upload-app -f App.ipa -t ios -u "$APPLE_ID" -p "$APP_SPECIFIC_PASSWORD"

# Using Fastlane / ASC API
fastlane deliver --skip_binary_upload true --metadata_path ./fastlane/metadata
```
