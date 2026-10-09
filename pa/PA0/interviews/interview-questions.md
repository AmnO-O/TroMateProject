# TroMate — Bộ câu hỏi phỏng vấn người dùng

*Elements of Software Engineering — 24A01 · PA0 User Research*

**Bản khảo sát online (Google Form):** https://docs.google.com/forms/d/e/1FAIpQLScM5yP4aliMYLqN7aDY88b7SqNZ4aVUaF5TYSiHEhPrL0CenA/viewform

---

## PHẦN 0 — MỞ ĐẦU & THÔNG TIN CÁ NHÂN

**Lời mở đầu (đọc trước khi bắt đầu):**
> Chào bạn, mình là [tên] thuộc nhóm đồ án môn Kỹ thuật phần mềm, đang tìm hiểu về cách mọi người quản lý chi tiêu phòng trọ. Buổi trò chuyện khoảng 10–15 phút thôi, mình xin phép **ghi âm lại** để ghi chép cho chính xác — bạn đồng ý không?

**Câu hỏi khởi động:**

- **Tên & tuổi:** Bạn tên gì và năm nay bao nhiêu tuổi?
- **Ngành học:** Bạn đang học ngành gì, năm thứ mấy, ở trường nào?
- **Sở thích:** Ngoài giờ học, bạn có sở thích gì?
- **Nơi ở:** Bạn đang ở trọ/ở ghép với mấy người?

---

## PHẦN 1 — BỐI CẢNH & THÓI QUEN HIỆN TẠI (CONTEXT)

1. **Quy trình hiện tại:** Hiện tại phòng bạn có mấy người, và mọi người đang chia tiền nhà cũng như chi phí sinh hoạt hàng ngày theo cách nào?
2. **Phân công trách nhiệm:** Ai là người đứng ra gom tiền, tính toán và thanh toán các hóa đơn (điện, nước, tiền nhà, WiFi) với chủ trọ mỗi tháng?

---

## PHẦN 2 — ĐÀO SÂU NỖI ĐAU & LÝ DO CÁC CÁCH CŨ THẤT BẠI (PAIN POINTS)

3. **Thất bại của giải pháp hiện có:** Phòng bạn đã từng dùng thử Google Sheets, Sổ tay hay các app chia tiền như Splitwise chưa? Lý do tại sao phòng bạn lại bỏ/không duy trì cách đó nữa?
4. **Mất mát từ vi chi phí (Micro-debts):** Các khoản mua đồ dùng chung nhỏ nhặt (gia vị, nước uống, giấy vệ sinh, xà phòng) thường được ghi lại ra sao? Đã bao giờ bạn vì ngại gõ nốt mà chấp nhận bỏ qua, tự trả tiền túi chưa?
5. **Độ phức tạp của hóa đơn trọ:** Việc ngồi cộng trừ chỉ số điện/nước cũ − mới và bóc tách hóa đơn viết tay của chủ nhà mỗi cuối tháng mất bao nhiêu thời gian? Đã từng có tranh cãi hay nhầm lẫn nào xảy ra chưa?
6. **Tâm lý rào cản:** Bạn cảm thấy thế nào khi phải nhắn tin đòi tiền bạn cùng phòng? Đã từng gặp trường hợp nhắn tin nhắc nợ nhưng bị bơ hoặc quên chưa?

---

## PHẦN 3 — KIỂM CHỨNG GIẢI PHÁP TROMATE (SOLUTION VALIDATION)

7. **Nhập liệu tự nhiên (NLP):** Nếu chỉ cần gõ một câu nhắn tin bình thường ngay trong box chat nhóm Telegram/Zalo (như *"A mua nước 50k chia cả phòng"*), con Bot sẽ tự bóc tách và ghi sổ, bạn thấy tính năng này có đủ tiện để bạn dùng hàng ngày không?
8. **Đọc hóa đơn tự động (OCR):** Nếu chỉ cần chụp ảnh tờ hóa đơn tiền nhà (kể cả viết tay), Bot tự nhận diện số điện/nước và ra ngay con số từng người phải trả, bạn có tin tưởng độ chính xác của nó không? Bạn có muốn tính năng xem lại ảnh gốc để đối soát không?
9. **Tối ưu dòng tiền & VietQR:** Việc Bot tự động triệt tiêu nợ vòng tròn (chuyển 3-4 giao dịch rườm rà thành 1 giao dịch duy nhất) và tạo sẵn mã VietQR có sẵn số tiền chính xác đến từng đồng giúp ích gì cho bạn?
10. **Giảm căng thẳng bằng Meme:** Việc Bot tự động tag tên gửi ảnh chế (meme) nhắc nợ nhẹ nhàng sau 24h có giúp giải quyết cảm giác "ngại đi đòi tiền" của bạn không?

---

## PHẦN 4 — RÀO CẢN & MỨC ĐỘ SẴN SÀNG SỬ DỤNG (ADOPTION & OBSTACLES)

11. **Rào cản lớn nhất:** Theo bạn, lý do lớn nhất khiến bạn hoặc bạn cùng phòng **KHÔNG CHỊU sử dụng** con Bot này là gì (ví dụ: sợ rò rỉ dữ liệu, ngại dùng Telegram/Zalo, không thích thao tác với Bot...)?
12. **Sự sẵn lòng (Willingness):** Trên thang điểm từ 1 đến 5, mức độ bạn sẵn sàng mời bạn cùng phòng trải nghiệm thử con Bot TroMate này ngay hôm nay là bao nhiêu?

---