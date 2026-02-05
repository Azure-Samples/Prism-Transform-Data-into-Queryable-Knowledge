# Third-Party Licenses

This project (PrismRAG) is licensed under the MIT License. However, it depends on third-party packages with more restrictive licenses that may affect how you can use, distribute, or deploy this software.

## Packages with Restrictive Licenses

| Package | License | Concern |
|---------|---------|---------|
| extract_msg | GPL 3.0 | Copyleft license |
| PyMuPDF | AGPL 3.0 | Requires source code disclosure, including for web services |
| pymupdf4llm | AGPL 3.0 | Requires source code disclosure, including for web services |
| pymupdf_layout | Commercial | Requires paid license from Artifex |

## License Implications

### AGPL 3.0 (PyMuPDF, pymupdf4llm)

The GNU Affero General Public License v3.0 (AGPL 3.0) is the most restrictive of these licenses. Key requirements:

1. **Source Code Disclosure**: If you deploy this software as a web service (which is how PrismRAG is designed to run), you must make the complete source code available to all users who interact with that service over a network.

2. **Copyleft**: Any modifications or derivative works must also be licensed under AGPL 3.0.

3. **License Preservation**: You must include the AGPL 3.0 license text and copyright notices in all copies.

For commercial use where source code disclosure is not acceptable, Artifex Software offers commercial licenses for PyMuPDF. See: https://pymupdf.io/

### GPL 3.0 (extract_msg)

The GNU General Public License v3.0 (GPL 3.0) is a copyleft license that requires:

1. **Copyleft**: Derivative works must also be licensed under GPL 3.0.

2. **Source Code Distribution**: If you distribute binaries, you must also provide source code or a written offer to provide source code.

3. **License Preservation**: You must include the GPL 3.0 license text and copyright notices.

Note: GPL 3.0 (unlike AGPL) does not have the network use provision, so running as a web service without distribution may not trigger the copyleft requirements. However, legal interpretation varies.

### Commercial License (pymupdf_layout)

The pymupdf_layout package requires a commercial license from Artifex Software. If you are using layout analysis features, you must obtain appropriate licensing.

Contact Artifex Software for licensing: https://artifex.com/

## Alternatives

If these license restrictions are problematic for your use case, consider these alternatives:

| Restricted Package | Alternative | License |
|--------------------|-------------|---------|
| PyMuPDF / pymupdf4llm | pdfplumber, pypdf, pdfminer.six | MIT / BSD |
| extract_msg | email (stdlib), python-oxmsg | Built-in / MIT |
| pymupdf_layout | (N/A - layout analysis requires commercial tools or custom implementation) | - |

Note: Alternative packages may have different capabilities and performance characteristics.

## Compliance

To comply with the AGPL 3.0 license when deploying PrismRAG as a web service:

1. Make the complete source code of your deployment available to users
2. Include all license texts (AGPL 3.0, GPL 3.0) with the deployment
3. Preserve all copyright notices
4. Document any modifications you have made

Or, contact Artifex Software to obtain a commercial license for PyMuPDF that does not require source code disclosure.

## Disclaimer

This document is provided for informational purposes and does not constitute legal advice. Consult with a legal professional to understand your specific obligations under these licenses.
