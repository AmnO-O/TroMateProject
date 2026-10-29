&lt;Team Name&gt;

# &lt;Project Name&gt;

## Use-Case Specification: &lt;Use-Case Name&gt;

**Version &lt;1.0&gt;**

> *[Note: The following template is provided for use with the Rational Unified Process. Text enclosed in square brackets and displayed in blue italics (style=InfoBlue) is included to provide guidance to the author and should be deleted before publishing the document. A paragraph entered following this style will automatically be set to normal (style=Body Text).]*

> *[To customize automatic fields in Microsoft Word (which display a gray background when selected), select File>Properties and replace the Title, Subject and Company fields with the appropriate information for this document. After closing the dialog, automatic fields may be updated throughout the document by selecting Edit>Select All (or Ctrl-A) and pressing F9, or simply click on the field and press F9. This must be done separately for Headers and Footers. Alt-F9 will toggle between displaying the field names and the field contents. See Word help for more information on working with fields.]*

| &lt;Project Name&gt; | Version: &lt;1.0&gt; |
| --- | --- |
| Use-Case Specification: &lt;Use-Case Name&gt; | Date: &lt;dd/mmm/yy&gt; |
| &lt;document identifier&gt; |  |

## Revision History

| Date | Version | Description | Author |
| --- | --- | --- | --- |
| &lt;dd/mmm/yy&gt; | &lt;x.x&gt; | &lt;details&gt; | &lt;name&gt; |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

## Table of Contents

1. Use-case Model — 4
2. Use-case Specifications — 4
   - 2.1 Use-case: Add a product to cart — 4
   - 2.2 Use-case: Create a new account — 5

## 1. Use-case Model

*[Put an image of the use-case diagram modeling all use-cases in this section]*

![Use-case model diagram](assets/use-case-diagram.png)

## 2. Use-case Specifications

### 2.1 Use-case: Add a product to cart

| Use case Name | Add a product to cart. |
| --- | --- |
| Brief description | This use case describes how the Customer can buy a product. |
| Actors | Customer |
| Basic Flow | 1. At the homepage, the user enters keywords on the ‘Search’ field<br>2. Users clicks on ‘Search’ button to start searching a product<br>3. System displays the products found<br>4. User clicks ‘Add to cart’ button on the expected product<br>5. System adds a new product to shopping cart<br>6. System displays the quantity of all products in the cart to the user |
| Alternative Flows | **Alternative flow 1: User cannot find products searched**<br>1. From #1 of the basic flow, user enters another term<br>2. Continue step #2 in the basic flow<br><br>**Alternative flow 2: Shopping cart has already had the product**<br>1. From #5 of the basic flow, system increases the quantity of the product<br>2. Continue step #6<br><br>**Alternative flow 3: …** |
| Pre-conditions | User goes to homepage at www.hailua.com.vn |
| Post-conditions | The user successfully adds new item to the cart or increases quantity of the existing item in the cart. |

### 2.2 Use-case: Create a new account

....

---

Confidential · © &lt;Company Name&gt;, 2026
