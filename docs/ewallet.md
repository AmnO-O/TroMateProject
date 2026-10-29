Reporter: Cao Quang Hung - 24125010
Date: 29 Oct 2026

## Issues
**Context**:
B nợ A (amount: x)
B muốn thanh toán cho A.

**Use Goal**:
- (1) Muốn tối đa automation trong quá trình chuyển tiền. Hướng tới 1 click
- (2) A phải nhận được thông báo sau khi B chuyển tiền và tự động cập nhật trạng thái trên TroMate.

**Research Goal**:
- from goal2 -> cần webhook api từ ewallet bắn về backend sau khi giao dịch thành công ***(i)***.  
- from goal1 
	- Liên kết ewallet như các ứng dụng Grab/Bee/..., trừ tiền sau 1 click ***(ii)***
	- Nhận thông tin từ TroMate, navigate QR/MoMo và điền sẵn các thông tin, đợi người dùng bấm nút chuyển tiền và xác thực. ***(iii)***

**UseCase UX Flow**:
1. B vào thanh toán cho A
2. Thanh toán:
	1. 1 click với ví điện tử
	2. navigate, fill in -> user confirm.
3. A, B mở TroMate và thấy khoản nợ đã được paid (backend recieve transaction success noti from webhook api)

---
## i. research on Webhook 

IPN được MoMo công bố cho các giao dịch thanh toán của đối tác (Merchant), không phải một API công khai để theo dõi mọi giao dịch chuyển tiền giữa hai ví MoMo cá nhân.

| Tình huống                                             | Khả năng sử dụng IPN                                    |
| ------------------------------------------------------ | ------------------------------------------------------- |
| User thanh toán đơn hàng cho Merchant qua MoMo         | Có                                                      |
| Backend Merchant xác nhận thanh toán thành công        | Có                                                      |
| User thanh toán qua MoMo rồi đóng trình duyệt          | Vẫn có thể nhận IPN                                     |
| ==A chuyển tiền trực tiếp cho ví cá nhân B==           | ==Chưa có API IPN công khai được xác nhận==             |
| ==Tromate nhận webhook mỗi khi B nhận tiền từ A==      | ==Không được hỗ trợ bởi tài liệu IPN Merchant hiện có== |
| Backend truy vấn một giao dịch Merchant bằng `orderId` | Có                                                      |


==🔴Điều khoản sử dụng==

| Điều kiện         | Yêu cầu                                                                               |
| ----------------- | ------------------------------------------------------------------------------------- |
| Tài khoản         | Đăng ký M4B                                                                           |
| Hồ sơ pháp lý     | ==🔴Thông tin đơn vị kinh doanh, giấy tờ và hợp đồng theo yêu cầu==                   |
| Môi trường Test   | Có thể tích hợp sau khi đăng ký thành công                                            |
| Kiểm thử          | SIT/UAT và đánh giá tích hợp                                                          |
| Production        | Xác thực hồ sơ và được MoMo cấp quyền                                                 |
| Phí sử dụng       | Theo chính sách và thỏa thuận áp dụng; chưa xác minh được mức phí IPN riêng công khai |
| Dữ liệu giao dịch | Phải bảo mật credentials, xác minh tính toàn vẹn và xử lý dữ liệu theo quy định       |

Tóm lại phải đăng ký M4B với MoMo, khai báo các hồ sơ pháp lý. Chỉ có thể test khi đăng ký thành công.

=> Do đó goal 2: update TroMate sau khi ghi nhận success transaction là ==🔴không khả thi đối với quy mô project môn học==.

## ii. Thanh toán 1 click với ewallet
**Account Binding + Tokenization Payment** (Thanh toán liên kết ví).

MoMo chính thức cung cấp API cho phép người dùng liên kết ví với một ứng dụng bên thứ ba (Grab, Bee, GreenXM đã sử dụng) và thực hiện các khoản thanh toán tiếp theo mà ==🟢không cần mở MoMo để xác nhận lại trong mọi giao dịch==.

1. Technical feasibility: MoMo có API hỗ trợ liên kết ví và thanh toán nhanh. Điều này đã được xác nhận.
2. Business eligibility: ==🔴API này dành cho đối tác/merchant==. Việc TroMate được phép sử dụng nó cho thanh toán nợ giữa các cá nhân vẫn cần MoMo phê duyệt.

...

## iii. navigate sang MoMo / Bank app

**MoMo One-Time Payment API**:
1. TroMate chuẩn bị amount, orderId, orderInfo
2. POST /v2/gateway/api/create
3. MoMo Payment Gateway: Trả về payUrl / deeplink
4. Mở MoMo bằng deeplink, lúc này màn hình trên MoMo đã fill sẵn các thông tin
5. Bấm xác nhận thanh toán 

==🔴Điều khoản sử dụng==: 
MoMo yêu cầu `partnerCode`, `accessKey`, `secretKey` và đăng ký MoMo for Business (M4B). Bạn có thể nhận test credentials sau khi đăng ký, nhưng để chạy Production phải hoàn thành xác thực hồ sơ và quy trình tích hợp. Riêng việc sử dụng `deeplink` trong Production cũng cần xin quyền MoMo.

Chưa tìm thấy public API hoặc URL scheme được MoMo chính thức cho phép để tự xây dựng link chứa `amount`, `orderInfo` rồi mở thẳng màn hình xác nhận.

Tóm lại cái này cũng phải đăng ký merchant.


## Đề xuất MVP
Người chuyển tiền upload bill chuyển khoản.
Người nhận manually check và confirm.

Cũng khá hợp lý, vì một vài lý do sau đây:
- Đối với góc nhìn người chuyển khoản: hơi cực, phải tự đi kiếm stk rồi nhập thông tin chuyển khoản, chụp màn hình và gửi. Có thể support bằng cách gắn sẵn số tài khoản trên TroMate để họ khỏi đi kiếm lại. Tự động lấy ảnh chụp bill trong gallery ra sau khi họ screenshot và quay lại màn hình TroMate.
- Đối với người nhận: vì tiền bạc là vấn đề nhạy cảm cần phải check kỹ, do đó việc tăng friction như vậy giúp học alert hơn về các khoản thu chi. Đây có thể coi như là một giải pháp hợp lý đối với ưng dụng tài chính hơn so với automate mọi thứ.


## Summary
Tóm lại để liên kết ví điện tử như MoMo, ZaloPay, ShopeePay cần phải đăng ký tài khoản doanh nghiệp và khai báo các giấy tờ pháp lý. 

Công ty ma như TroMate thì khó nói.



