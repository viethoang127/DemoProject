# Detect Fake News 

Hệ thống kiểm tra tính xác thực của thông tin thời tiết bằng cách đối chiếu câu hỏi với dữ liệu thời tiết chính thống, tìm kiếm thông tin liên quan trong cơ sở dữ liệu và sử dụng mô hình ngôn ngữ để đưa ra kết luận

# Mục tiêu
- Phân tích thời gian và địa điểm trong câu hỏi.
- Thu thập dữ liệu thời tiết từ nguồn chính thống.
- Tìm đoạn thông tin phù hợp bằng embedding và ChromaDB.
- Kết luận câu hỏi dưới dạng REAL, FAKE hoặc UNCERTAIN.

# Luồng xử lý
1. Crawl dữ liệu thời tiết từ các nguồn chính thức.
2. Làm sạch văn bản và chuẩn hóa tiếng Việt.
3. Chia dữ liệu thành các chunk nhỏ để lưu trữ.
4. Trích xuất thời gian, địa điểm và các biểu thức thời gian từ truy vấn.
5. Tìm kiếm văn bản tương đồng trong ChromaDB.
6. Dùng LLM để đánh giá.

# Công dụng của từng thư mục

- collection: Thu thập bài viết và dữ liệu thời tiết từ các nguồn chính thống.
- clean_data: Làm sạch, chuẩn hóa và token hóa nội dung văn bản.
- chunking: Chia bài viết thành các đoạn nhỏ để dễ tìm kiếm và xử lý.
- model_embedding: Chuyển văn bản thành vector và tìm kiếm nội dung tương đồng.
- query_parser: Phân tích câu hỏi, xác định thời gian, địa điểm và nội dung chính.
- LLM_reasoning: Dùng LLM để đánh giá và đưa ra kết luận.
- services: Điều phối quá trình crawl, xử lý và đồng bộ dữ liệu.
- storage: Khởi tạo database và quản lý dữ liệu trong SQLite.
- temporal: Nhận diện ngày tháng, khoảng thời gian và các mốc thời gian trong văn bản.
- evaluation: Tạo dữ liệu kiểm thử và đánh giá hiệu quả hệ thống.
- chroma_db: Lưu trữ dữ liệu vector phục vụ việc tìm kiếm evidence.




