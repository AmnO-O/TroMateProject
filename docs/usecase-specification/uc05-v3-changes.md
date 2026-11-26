# UC05 Confirm, Reject or Edit Pending Expense: những gì cần cập nhật theo spec v3.0

Spec: [usecase-specification-v3.0.docx](usecase-specification-v3.0.docx). Xem mục 1.3 (BR01, BR02, BR04) và mục 2.5 (UC05). Chữ xanh trong file là phần thay đổi so với v2.

Spec v3 thay đổi UC05 ở ba điểm chính:
- **Creator luôn là payer**, và **chỉ creator được Edit/Cancel**.
- **Participant chỉ được Agree hoặc Reject**, và Reject bắt buộc phải có lý do. Creator chịu trách nhiệm sửa khoản chi dựa trên lý do đó.
- **Tin nhắn cũ trong group** không còn bấm được sau khi khoản chi bị sửa.

## 1. Quyền theo vai trò (BR04)

| Vai trò | v2.0 | v3.0 |
|---|---|---|
| Creator (= payer) | Như mọi người liên quan, thêm Cancel; khi Disputed được Edit/Cancel | **Edit, Cancel**, cả khi Pending lẫn Disputed. Agreement được ghi nhận sẵn từ lúc Share |
| Participant | Agree, Reject, **Edit** | **Agree, Reject** (có lý do). Khi Disputed: được **Add reason** |
| Người không liên quan | Chỉ xem | Chỉ xem (không đổi) |

Payer không còn là một vai trò riêng, vì creator và payer là cùng một người (BR01).

## 2. Thay đổi trong flow

**Basic flow**
- **Bước 1:** nút hiển thị **theo vai trò** của người xem. Participant thấy Agree/Reject, creator thấy Edit/Cancel expense. Trước đây ai cũng thấy Agree/Reject/Edit, và không có nút Cancel.
- **Bước 2–3:** đổi chữ "member" thành "participant". Logic không đổi.

**UC05-AF02 Participant rejects the expense**
- Lý do Reject là **bắt buộc**. Danh sách lý do giữ nguyên: sai số tiền, sai người tham gia, không phải khoản của tôi, trùng lặp, hoặc tự ghi chú.
- Lý do được **gửi cho creator** để creator sửa. Những người liên quan khác được thông báo.
- **Mới:** khi khoản chi còn Disputed, TroMate **nhắc creator mỗi 3 ngày** cho tới khi creator Edit hoặc Cancel. Hệ thống **không bao giờ tự hủy**, vì đây là tiền của creator và creator phải tự chịu trách nhiệm.

**UC05-AF03 Creator edits the expense** (trước đây là "Member edits")
- **Chỉ creator** được làm.
- Khi mở màn hình Edit, hiển thị **tất cả lý do Reject**.
- Được sửa số tiền, category, participants và cách chia. **Không được đổi payer.**
- Sau khi lưu:
  - Tạo version mới, xóa mọi agreement trừ của creator, đưa trạng thái về Pending.
  - **Kiểm tra lại điều kiện auto-confirm (BR02).** Ví dụ đổi category sang Rent/Utilities thì bỏ deadline.
  - Nếu khoản chi vẫn đủ điều kiện thì chạy lại window **với độ dài đã lưu lúc Share**, không lấy window hiện tại của phòng.
  - Cài đặt bật/tắt auto-confirm **không đổi được** khi Edit.
  - Báo cho người liên quan, kèm phần thay đổi được highlight.
  - **Mới:** báo riêng cho người **được thêm vào** và người **bị bỏ ra** trong lần sửa này.
  - **Mới:** các tin nhắn cũ của khoản chi trong group được đánh dấu **outdated** và bị gỡ nút.

**UC05-AF06 Expense is disputed and the member is not the creator**
- Hiển thị **tất cả** lý do Reject (trước đây chỉ một lý do).
- **Mới:** participant có nút **Add reason**.

**UC05-AF07 Member is not involved:** chỉ sửa câu chữ ("neither the creator (the payer) nor a participant"). Hành vi không đổi.

**Alternative flow mới**
- **UC05-AF08 Member acts on an outdated message:** khi ai đó bấm nút trên tin nhắn của version cũ, hoặc trên khoản chi không còn Pending, hệ thống **không ghi nhận**, báo khoản chi đã thay đổi, rồi hiển thị version hiện tại kèm phần thay đổi được highlight. Sau đó quay về bước 1. Nếu khoản chi đã đóng thì bước 1 đi tiếp vào AF05.
- **UC05-AF09 Participant adds a reason to a disputed expense:** participant chọn lý do. Lý do được thêm vào khoản chi và gửi cho creator. Khoản chi vẫn Disputed.

**Không đổi:** AF01 (còn người chưa agree), AF04 (creator hủy), AF05 (khoản chi đã đóng), pre-conditions và post-conditions (chỉ sửa câu chữ).

## 3. Ngoài phạm vi UC05, nhưng liên quan

- **UC03b-AF06:** khi nhập hoặc sửa khoản chi, mô tả nói người khác trả thì bị từ chối (payer luôn là creator).
- **UC06-AF05:** nhắc participant chưa phản hồi 24 giờ trước deadline (chỉ với window dài hơn 1 ngày). Phần này do người làm UC06 phụ trách.
- **BR12:** không cho rời phòng khi còn liên quan tới khoản chi Pending/Disputed, hoặc khi balance khác 0. Vì vậy UC05 không phải xử lý trường hợp creator hay participant rời phòng giữa chừng.

## 4. Test

Test case UC05 cũ cần sửa:
- Participant thấy nút **Edit**: sai, giờ participant chỉ thấy Agree/Reject.
- "Involved member edits a Pending expense": đổi thành creator Edit, và thêm case participant **không** được Edit.
- Case kỳ vọng "Cancel expense is not offered": vẫn đúng với participant. Thêm case creator **được thấy** nút Cancel.

Cần thêm:
- Reject mà không chọn lý do: không cho Reject.
- Creator Edit: agreement của participant bị xóa, window chạy lại theo độ dài lúc Share.
- Edit đổi category sang Rent: khoản chi không còn deadline.
- Edit thêm hoặc bỏ participant: người được thêm và người bị bỏ đều nhận thông báo riêng.
- Bấm Agree trên tin nhắn của version cũ: không ghi nhận, hiển thị version mới (AF08).
- Bấm nút trên khoản chi đã Confirmed/Cancelled: không ghi nhận (AF08 rồi tới AF05).
- Participant Add reason khi Disputed: creator nhận được lý do (AF09).
- Khoản chi Disputed quá 3 ngày: creator được nhắc, khoản chi không tự hủy.
