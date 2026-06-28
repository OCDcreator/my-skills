// review_gui.cpp — EUI-NEO 翻译审核台 (MVP)
//
// 用法（通过环境变量传参，因为 EUI-NEO 接管了 main）：
//   set REVIEW_IN=输入.json
//   set REVIEW_OUT=输出.json
//   review_gui.exe
//
// 读取 REVIEW_IN 显示成可勾选/可编辑的列表，
// 人审核后点"应用并导出"写 REVIEW_OUT，关窗退出。
// 退出码: 0=已导出, 1=未导出直接关窗

#include "eui_neo.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <functional>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

// ============================================================================
// 极简 JSON 解析器（自包含，无第三方依赖）
// ============================================================================
namespace minjson {
struct Value {
    enum Type { Null, Bool, String, Array, Object } type = Null;
    bool b = false;
    std::string s;
    std::vector<Value> arr;
    std::vector<std::pair<std::string, Value>> obj;
    const Value* find(const std::string& key) const {
        if (type != Object) return nullptr;
        for (auto& kv : obj) if (kv.first == key) return &kv.second;
        return nullptr;
    }
};
struct Parser {
    const char* p; const char* end;
    void skipWs() { while (p < end && (*p==' '||*p=='\t'||*p=='\n'||*p=='\r')) p++; }
    bool parse(Value& out) {
        skipWs();
        if (p >= end) return false;
        char c = *p;
        if (c == '{') return parseObject(out);
        if (c == '[') return parseArray(out);
        if (c == '"') { out.type = Value::String; return parseString(out.s); }
        if (c == 't' || c == 'f') return parseBool(out);
        if (c == 'n') { out.type = Value::Null; return parseLiteral("null"); }
        return parseNumber(out);
    }
    bool parseString(std::string& out) {
        if (*p != '"') return false;
        p++; out.clear();
        while (p < end && *p != '"') {
            if (*p == '\\' && p + 1 < end) {
                p++; char e = *p;
                if (e=='n') out+='\n'; else if (e=='t') out+='\t';
                else if (e=='r') out+='\r'; else if (e=='"') out+='"';
                else if (e=='\\') out+='\\'; else if (e=='/') out+='/';
                else if (e=='u' && p+4<end) {
                    int code=0;
                    for (int i=0;i<4;i++){char h=p[1+i];code<<=4;
                        if(h>='0'&&h<='9')code|=h-'0';
                        else if(h>='a'&&h<='f')code|=h-'a'+10;
                        else if(h>='A'&&h<='F')code|=h-'A'+10;}
                    p+=4;
                    if(code<0x80) out+=static_cast<char>(code);
                    else if(code<0x800){out+=static_cast<char>(0xC0|(code>>6));out+=static_cast<char>(0x80|(code&0x3F));}
                    else{out+=static_cast<char>(0xE0|(code>>12));out+=static_cast<char>(0x80|((code>>6)&0x3F));out+=static_cast<char>(0x80|(code&0x3F));}
                } else out+=e;
                p++;
            } else { out += *p; p++; }
        }
        if (p >= end) return false;
        p++; return true;
    }
    bool parseObject(Value& out) {
        out.type = Value::Object; p++; skipWs();
        if (p<end && *p=='}') { p++; return true; }
        while (p<end) {
            skipWs(); std::string key;
            if (!parseString(key)) return false;
            skipWs();
            if (p>=end || *p!=':') return false;
            p++; Value v;
            if (!parse(v)) return false;
            out.obj.emplace_back(std::move(key), std::move(v));
            skipWs();
            if (p<end && *p==',') { p++; continue; }
            if (p<end && *p=='}') { p++; return true; }
            return false;
        }
        return false;
    }
    bool parseArray(Value& out) {
        out.type = Value::Array; p++; skipWs();
        if (p<end && *p==']') { p++; return true; }
        while (p<end) {
            Value v;
            if (!parse(v)) return false;
            out.arr.push_back(std::move(v));
            skipWs();
            if (p<end && *p==',') { p++; continue; }
            if (p<end && *p==']') { p++; return true; }
            return false;
        }
        return false;
    }
    bool parseBool(Value& out) {
        if (end-p>=4 && strncmp(p,"true",4)==0){out.type=Value::Bool;out.b=true;p+=4;return true;}
        if (end-p>=5 && strncmp(p,"false",5)==0){out.type=Value::Bool;out.b=false;p+=5;return true;}
        return false;
    }
    bool parseLiteral(const char* lit) {
        size_t n=strlen(lit);
        if (size_t(end-p)>=n && strncmp(p,lit,n)==0){p+=n;return true;}
        return false;
    }
    bool parseNumber(Value& out) {
        const char* start=p;
        while (p<end && (*p=='-'||*p=='+'||*p=='.'||(*p>='0'&&*p<='9')||*p=='e'||*p=='E')) p++;
        out.type=Value::String; out.s.assign(start,p); return p>start;
    }
};
bool parse(const std::string& text, Value& out) {
    Parser ps{ text.c_str(), text.c_str()+text.size() };
    return ps.parse(out);
}
} // namespace minjson

std::string escapeJson(const std::string& s) {
    std::string out; out.reserve(s.size()+8);
    for (char c : s) {
        switch (c) {
            case '"': out+="\\\""; break;
            case '\\': out+="\\\\"; break;
            case '\n': out+="\\n"; break;
            case '\r': out+="\\r"; break;
            case '\t': out+="\\t"; break;
            default:
                if (static_cast<unsigned char>(c)<0x20){char b[8];snprintf(b,sizeof(b),"\\u%04x",c);out+=b;}
                else out+=c;
        }
    }
    return out;
}

// ============================================================================
// 全局状态（EUI-NEO 接管 main，必须用全局变量）
// ============================================================================
struct ReviewEntry {
    std::string id, method, original, translation, context;
    bool enabled = true;
    bool edited = false;
};
struct AppState {
    std::string plugin, version, targetLanguage="zh-cn";
    std::vector<ReviewEntry> entries;
    std::string statusText;
    std::string searchQuery;              // 工具栏搜索框内容（匹配原文/译文/method/id）
    bool showOnlyUntranslated = false;    // "仅未翻译" 过滤开关
    bool shouldExport = false;
    bool loaded = false;
};

// 一条是否算"未翻译"：译文为空 / 全空白 / 与原文完全相同
// （沿用 i18n AST 编辑器对 untranslated 的判定口径）
bool isUntranslated(const ReviewEntry& e) {
    bool blank = true;
    for (char c : e.translation) if (c != ' ' && c != '\t' && c != '\n' && c != '\r') { blank = false; break; }
    return blank || e.translation == e.original;
}

// ----------------------------------------------------------------------------
// UTF-8 辅助：估算一段文本在给定宽度内换行后的行数。
// EUI-NEO 的 text 组件 .wrap(true) 会按宽度自动换行，但行高/行数要我们自己
// 给 size，所以这里用启发式预估行数，确保多行文本有足够高度完整显示。
// ----------------------------------------------------------------------------
float estimatedCharWidth(uint32_t cp, float fontSize) {
    // CJK / 全角标点按全宽，其余按半宽
    if ((cp >= 0x1100 && cp <= 0x115F) || (cp >= 0x2E80 && cp <= 0x9FFF) ||
        (cp >= 0xA000 && cp <= 0xA4CF) || (cp >= 0xAC00 && cp <= 0xD7A3) ||
        (cp >= 0xF900 && cp <= 0xFAFF) || (cp >= 0xFE30 && cp <= 0xFE4F) ||
        (cp >= 0xFF00 && cp <= 0xFF60) || (cp >= 0xFFE0 && cp <= 0xFFE6) ||
        cp == 0x3000) {
        return fontSize * 1.0f;
    }
    return fontSize * 0.55f;
}
int estimateWrappedLines(const std::string& s, float width, float fontSize) {
    if (width <= 1.0f) return 1;
    int lines = 1;
    float cur = 0.0f;
    size_t i = 0;
    while (i < s.size()) {
        unsigned char c = static_cast<unsigned char>(s[i]);
        uint32_t cp = 0; size_t len = 1;
        if (c < 0x80) { cp = c; len = 1; }
        else if ((c >> 5) == 0x06) { cp = c & 0x1F; len = 2; }
        else if ((c >> 4) == 0x0E) { cp = c & 0x0F; len = 3; }
        else if ((c >> 3) == 0x1E) { cp = c & 0x07; len = 4; }
        for (size_t k = 1; k < len && i + k < s.size(); ++k)
            cp = (cp << 6) | (static_cast<unsigned char>(s[i + k]) & 0x3F);
        if (cp == '\n') { lines++; cur = 0.0f; }
        else {
            float cw = estimatedCharWidth(cp, fontSize);
            if (cur + cw > width) { lines++; cur = cw; }
            else cur += cw;
        }
        i += len;
    }
    return lines < 1 ? 1 : lines;
}
static AppState g_state;
static std::string g_inPath;
static std::string g_outPath;

bool loadInput(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) { std::cerr << "[review_gui] 无法打开输入: " << path << "\n"; return false; }
    std::stringstream ss; ss << f.rdbuf();
    minjson::Value root;
    if (!minjson::parse(ss.str(), root)) { std::cerr << "[review_gui] JSON 解析失败\n"; return false; }
    if (auto* v=root.find("plugin")) g_state.plugin=v->s;
    if (auto* v=root.find("version")) g_state.version=v->s;
    if (auto* v=root.find("targetLanguage")) g_state.targetLanguage=v->s;
    if (auto* arr=root.find("entries")) {
        for (auto& e : arr->arr) {
            ReviewEntry re;
            if (auto* v=e.find("id")) re.id=v->s;
            if (auto* v=e.find("method")) re.method=v->s;
            if (auto* v=e.find("original")) re.original=v->s;
            if (auto* v=e.find("translation")) re.translation=v->s;
            if (auto* v=e.find("context")) re.context=v->s;
            if (auto* v=e.find("defaultEnabled")) re.enabled=v->b;
            g_state.entries.push_back(std::move(re));
        }
    }
    std::cerr << "[review_gui] 加载 " << g_state.entries.size() << " 条\n";
    return true;
}

bool writeOutput(const std::string& path, const std::string& status) {
    std::ofstream f(path, std::ios::binary);
    if (!f) return false;
    f << "{\n";
    f << "  \"plugin\": \"" << escapeJson(g_state.plugin) << "\",\n";
    f << "  \"version\": \"" << escapeJson(g_state.version) << "\",\n";
    f << "  \"targetLanguage\": \"" << escapeJson(g_state.targetLanguage) << "\",\n";
    f << "  \"status\": \"" << status << "\",\n";
    int enabledCount=0; for (auto& e:g_state.entries) if(e.enabled) enabledCount++;
    f << "  \"enabledCount\": " << enabledCount << ",\n";
    f << "  \"entries\": [\n";
    bool first=true;
    for (auto& e : g_state.entries) {
        if (!first) f << ",\n";
        first=false;
        f << "    {\"id\": \"" << escapeJson(e.id)
          << "\", \"original\": \"" << escapeJson(e.original)
          << "\", \"translation\": \"" << escapeJson(e.translation)
          << "\", \"enabled\": " << (e.enabled?"true":"false") << "}";
    }
    f << "\n  ]\n}\n";
    return true;
}

// 通过 atexit 在程序退出时保存（EUI-NEO 不暴露 shutdown 钩子给用户重写）
// 用 written 标志保证幂等：导出按钮已写过文件时，atexit 不再重复写
static bool g_written = false;
void onExit() {
    if (g_written || g_outPath.empty()) return;
    g_written = true;
    writeOutput(g_outPath, g_state.shouldExport ? "applied" : "cancelled");
    std::cerr << "[review_gui] 退出，写 " << (g_state.shouldExport?"applied":"cancelled")
              << " 到 " << g_outPath << "\n";
}

// ============================================================================
// EUI-NEO 界面
// ============================================================================
namespace app {

const DslAppConfig& dslAppConfig() {
    // 跨平台中文字体路径
#ifdef _WIN32
    const char* fontPath = "C:\\Windows\\Fonts\\msyh.ttc";
#elif defined(__APPLE__)
    const char* fontPath = "/System/Library/Fonts/STHeiti Light.ttc";
#else
    const char* fontPath = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc";
#endif
    static const DslAppConfig config = DslAppConfig{}
        .title("i18n Review Console")
        .pageId("review")
        .clearColor({0.10f, 0.11f, 0.13f, 1.0f})  // == palette::kBg，palette 定义在下方
        .windowSize(1000, 720)
        .textFont(fontPath);
    return config;
}

// ============================================================================
// 统一色板（基于 Kimi UI 评审，建立 background/surface/elevated 三级灰阶
// + 语义色：primary 仅留给主操作，状态色独立体系）
// ============================================================================
namespace palette {
// 基础灰阶（background < surface < elevated）
constexpr eui::Color kBg       {0.10f, 0.11f, 0.13f, 1.0f};  // 窗口背景（最深）
constexpr eui::Color kSurface  {0.14f, 0.15f, 0.18f, 1.0f};  // 列表行底
constexpr eui::Color kSurface2 {0.19f, 0.20f, 0.25f, 1.0f};  // 斑马纹次行（拉大对比）
constexpr eui::Color kElevated {0.21f, 0.22f, 0.27f, 1.0f};  // 按钮/顶栏底（最浅）
constexpr eui::Color kBorder   {0.27f, 0.29f, 0.35f, 0.90f}; // 分隔线/边框
constexpr eui::Color kBorderSoft{0.22f, 0.24f, 0.29f, 0.70f};
// 文本
constexpr eui::Color kTextHi   {0.95f, 0.97f, 1.00f, 1.0f};  // 主标题
constexpr eui::Color kTextBody {0.82f, 0.86f, 0.92f, 1.0f};  // 正文
constexpr eui::Color kTextMute {0.55f, 0.62f, 0.72f, 1.0f};  // 副标题/统计
constexpr eui::Color kTextDim  {0.42f, 0.48f, 0.56f, 1.0f};  // 占位/禁用
// 语义强调（primary 只给主按钮 + 已编辑态）
constexpr eui::Color kPrimary  {0.34f, 0.56f, 0.92f, 1.0f};  // 主操作蓝
constexpr eui::Color kEdited   {0.36f, 0.62f, 0.95f, 1.0f};  // 已编辑：蓝边框
// 状态色（独立体系，不与 primary 撞色）
constexpr eui::Color kUntranslatedBg  {0.19f, 0.17f, 0.12f, 1.0f}; // 未翻译：琥珀底
constexpr eui::Color kUntranslatedTint{0.88f, 0.72f, 0.36f, 1.0f}; // 未翻译标签字
constexpr eui::Color kSkippedBg       {0.11f, 0.12f, 0.14f, 0.55f};// 已跳过：半透明灰
constexpr eui::Color kSkippedText     {0.40f, 0.44f, 0.50f, 1.0f}; // 已跳过字
// method 标签：中性青灰，不再用蓝（避免与 primary 撞色）
constexpr eui::Color kMethod    {0.58f, 0.66f, 0.74f, 1.0f};
// hover 高亮
constexpr eui::Color kHover     {1.00f, 1.00f, 1.00f, 0.04f};
} // namespace palette

void compose(eui::Ui& ui, const eui::Screen& screen) {
    // 首次进入：惰性加载输入 + 注册退出钩子
    if (!g_state.loaded) {
        const char* inP = std::getenv("REVIEW_IN");
        const char* outP = std::getenv("REVIEW_OUT");
        if (inP) g_inPath = inP;
        if (outP) g_outPath = outP;
        if (!g_inPath.empty()) loadInput(g_inPath);
        std::atexit(onExit);
        g_state.loaded = true;
    }

    const float W = screen.width;
    const float H = screen.height;
    const int total = static_cast<int>(g_state.entries.size());
    int enabledCount=0, editedCount=0;
    for (auto& e:g_state.entries){ if(e.enabled)enabledCount++; if(e.edited)editedCount++; }

    ui.stack("root").size(W, H).content([&] {
        // ---- 顶栏（标题 + 统计；强调色只留给主操作，标题用中性高亮）----
        const float topH = 52.0f;
        ui.stack("top").size(W, topH).content([&] {
            ui.rect("top.bg").size(W, topH).color(palette::kElevated).build();
            ui.rect("top.bd").y(topH-1.0f).size(W,1.0f).color(palette::kBorder).build();
            ui.text("ttl").x(24.0f).y(9.0f).size(520.0f,20.0f)
                .text(g_state.plugin + " @" + g_state.version)
                .fontSize(16.0f).fontWeight(640).color(palette::kTextHi).build();
            ui.text("sub").x(24.0f).y(29.0f).size(700.0f,18.0f)
                .text(std::to_string(total) + " strings  ·  "
                      + std::to_string(enabledCount) + " enabled  ·  "
                      + std::to_string(editedCount) + " edited"
                      + (editedCount>0 ? "  ·  待保存" : ""))
                .fontSize(11.5f).color(editedCount>0 ? palette::kUntranslatedTint : palette::kTextMute)
                .build();
        });

        // ---- 工具栏（搜索 + 仅未翻译筛选）----
        const float toolH = 48.0f;
        const float toolY = topH;
        ui.stack("tool").position(0.0f, toolY).size(W, toolH).content([&] {
            ui.rect("tool.bg").size(W, toolH).color(palette::kBg).build();
            ui.rect("tool.bd").y(toolH-1.0f).size(W,1.0f).color(palette::kBorderSoft).build();

            // 搜索框（左，主力控件）
            const float schX = 24.0f;
            const float schW = 380.0f;
            ui.stack("schwrap").position(schX, (toolH-32.0f)*0.5f).size(schW, 32.0f).content([&] {
                components::input(ui, "search")
                    .size(schW, 32.0f)
                    .value(g_state.searchQuery)
                    .placeholder("搜索原文 / 译文 / id …")
                    .inset(10.0f)
                    .fontSize(13.0f)
                    .onChange([](const std::string& v){ g_state.searchQuery = v; })
                    .build();
            });

            // "仅未翻译" 筛选（secondary/toggle 态：激活才填色，否则 ghost）
            const int untranslatedTotal = static_cast<int>(
                std::count_if(g_state.entries.begin(), g_state.entries.end(), isUntranslated));
            const float fltX = schX + schW + 14.0f;
            const float fltW = 180.0f;
            ui.stack("fltw").position(fltX, (toolH-32.0f)*0.5f).size(fltW, 32.0f).content([&] {
                components::button(ui, "btnUntr").size(fltW,32.0f)
                    .text(std::string("未翻译 · ") + std::to_string(untranslatedTotal))
                    .fontSize(12.5f)
                    .theme(components::theme::dark(), g_state.showOnlyUntranslated)
                    .onClick([&]{
                        g_state.showOnlyUntranslated = !g_state.showOnlyUntranslated;
                        g_state.statusText = g_state.showOnlyUntranslated
                            ? "已开启：仅显示未翻译" : "已关闭过滤";
                    }).build();
            });
        });

        // ---- 中间滚动列表（变高行，原文/译文完整 wrap 显示）----
        // 先按搜索/筛选算出可见下标集合，再逐行预估高度，得到 contentH。
        // 这是变高行的关键：每行高度取决于原文/译文的换行行数，不再固定。
        std::vector<int> visible; visible.reserve(g_state.entries.size());
        for (int i = 0; i < total; ++i) {
            const ReviewEntry& e = g_state.entries[i];
            if (g_state.showOnlyUntranslated && !isUntranslated(e)) continue;
            if (!g_state.searchQuery.empty()) {
                const std::string& q = g_state.searchQuery;
                bool hit = e.id.find(q)!=std::string::npos || e.method.find(q)!=std::string::npos
                        || e.original.find(q)!=std::string::npos
                        || e.translation.find(q)!=std::string::npos;
                if (!hit) continue;
            }
            visible.push_back(i);
        }

        const float listY = toolY + toolH;
        const float botH = 56.0f;   // 与下方底栏高度一致
        const float listH = H - listY - botH - 24.0f;  // 底部留足余量，确保末行绝不被遮
        const float rowGap = 6.0f;

        components::scrollView(ui, "list")
            .x(0.0f).y(listY).size(W, listH).gap(0.0f)
            .contentKey(std::to_string(visible.size()) + "." +
                        (g_state.showOnlyUntranslated?"1":"0") + "." +
                        std::to_string(g_state.searchQuery.size()))
            .content([&](eui::Ui& sui, float contentW, float /*viewportH*/) {
                // 关键：EUI-NEO 的 scrollView 在出现滚动条时会从 contentW 里扣掉
                // scrollbarWidth(8) + scrollbarGap(16) = 24px；不出现时则不扣。
                // 这会导致"有滚动条 → 右边距突然变大"。
                // 解法：始终在自己布局里再预留一个固定 gutter（24px），让有无滚动条时
                // 行内容的右边界一致。
                const float gutter = 24.0f;
                const float usableW = std::max(200.0f, contentW - gutter);

                // 行内列布局（绝对坐标）
                const float padX = 14.0f;
                const float chkX = padX;
                const float chkW = 24.0f;
                const float leftX = chkX + chkW + 10.0f;
                const float leftW = 380.0f;
                const float inX = leftX + leftW + 12.0f;
                const float inW = std::max(140.0f, usableW - inX - padX);

                // 第一遍：预估每行高度（取原文/译文两列中较大的换行行数）
                const float origFont = 13.0f;
                const float origLineH = 18.0f;
                const float transFont = 14.0f;
                const float transLineH = 20.0f;
                const float methodH = 16.0f;
                const float verticalPad = 16.0f;  // 上下内边距合计

                std::vector<float> rowHeights(visible.size(), 64.0f);
                float cursorY = 8.0f;
                for (size_t vi = 0; vi < visible.size(); ++vi) {
                    const ReviewEntry& e = g_state.entries[visible[vi]];
                    int origLines = estimateWrappedLines(e.original, leftW, origFont);
                    int transLines = std::max(estimateWrappedLines(e.translation, std::max(80.0f, inW - 20.0f), transFont),
                                              isUntranslated(e) ? 1 : 1);
                    int maxLines = std::max({origLines, transLines, 1});
                    float textH = methodH + 4.0f + static_cast<float>(maxLines) * std::max(origLineH, transLineH);
                    rowHeights[vi] = std::max(64.0f, textH + verticalPad);
                    cursorY += rowHeights[vi] + rowGap;
                }
                cursorY += 10.0f;  // 末尾留白，确保滚到底时最后一行不被裁
                const float contentH = std::max(listH, cursorY);

                sui.stack("list.area")
                    .size(usableW, contentH)
                    .content([&] {
                        float rowY = 6.0f;
                        for (size_t vi = 0; vi < visible.size(); ++vi) {
                            const int idx = visible[vi];
                            ReviewEntry& e = g_state.entries[idx];
                            const std::string rid = "r" + std::to_string(vi);
                            const float rowH = rowHeights[vi];
                            const bool untr = isUntranslated(e);
                            const bool skipped = !e.enabled;

                            // 1) 行背景：状态优先级 跳过(灰) > 未翻译(琥珀) > 斑马纹
                            eui::Color bg = (vi % 2u == 0u) ? palette::kSurface : palette::kSurface2;
                            if (untr && !skipped) bg = palette::kUntranslatedBg;
                            if (skipped) bg = palette::kSkippedBg;
                            sui.rect(rid + ".bg")
                                .position(padX * 0.5f, rowY)
                                .size(usableW - padX, rowH)
                                .color(bg)
                                .radius(8.0f)
                                .border(1.0f, palette::kBorderSoft)
                                .build();

                            // 1b) 左侧状态指示竖条：已编辑=蓝，未翻译=琥珀，跳过=无
                            if (!skipped) {
                                eui::Color accent = e.edited ? palette::kEdited
                                              : untr  ? palette::kUntranslatedTint
                                              : eui::Color{0,0,0,0};
                                if (accent.a > 0.0f) {
                                    sui.rect(rid + ".bar")
                                        .position(padX * 0.5f + 1.0f, rowY + 6.0f)
                                        .size(4.0f, rowH - 12.0f)
                                        .color(accent)
                                        .radius(2.0f)
                                        .build();
                                }
                            }

                            // 2) checkbox（中性色，不再抢蓝色）
                            sui.stack(rid + ".chw")
                                .position(chkX, rowY + (rowH - 24.0f) * 0.5f)
                                .size(24.0f, 24.0f)
                                .content([&] {
                                    components::checkbox(sui, rid + ".chk")
                                        .size(24.0f, 24.0f)
                                        .checked(e.enabled)
                                        .boxSize(18.0f)
                                        .onChange([&e](bool v){
                                            e.enabled=v; e.edited=true;
                                            g_state.statusText = v ? "已启用" : "已跳过";
                                        })
                                        .build();
                                })
                                .build();

                            // 3) 方法标签 + 状态 badge（中性灰底 pill，状态用色点）
                            {
                                std::string label = e.method;
                                eui::Color tagColor = skipped ? palette::kSkippedText
                                                  : palette::kMethod;
                                // 状态 pill：始终显示，让状态列稳定可见
                                std::string statusTxt;
                                eui::Color statusBg{0,0,0,0};
                                eui::Color statusFg{0,0,0,0};
                                if (skipped)              { statusTxt="跳过"; statusBg=eui::Color{0.20f,0.21f,0.25f,0.9f}; statusFg=palette::kSkippedText; }
                                else if (e.edited)         { statusTxt="已编辑"; statusBg=eui::Color{0.16f,0.22f,0.34f,0.95f}; statusFg=palette::kEdited; }
                                else if (untr)             { statusTxt="未翻译"; statusBg=eui::Color{0.26f,0.22f,0.12f,0.95f}; statusFg=palette::kUntranslatedTint; }
                                else                       { statusTxt="就绪";   statusBg=eui::Color{0.18f,0.20f,0.24f,0.6f}; statusFg=palette::kTextMute; }
                                // method 文字
                                sui.text(rid + ".m")
                                    .position(leftX, rowY + 6.0f)
                                    .size(170.0f, methodH)
                                    .text("[" + label + "]")
                                    .fontSize(10.5f)
                                    .fontWeight(640)
                                    .color(tagColor)
                                    .verticalAlign(eui::VerticalAlign::Center)
                                    .build();
                                // 状态 pill：带圆角背景 + 文字，比小点醒目得多
                                {
                                    const float pillX = leftX + 176.0f;
                                    const float pillW = 52.0f;
                                    const float pillH = 15.0f;
                                    sui.rect(rid + ".pill")
                                        .position(pillX, rowY + 6.0f + (methodH - pillH)*0.5f)
                                        .size(pillW, pillH)
                                        .color(statusBg)
                                        .radius(pillH * 0.5f)
                                        .build();
                                    sui.text(rid + ".st")
                                        .position(pillX, rowY + 6.0f + (methodH - pillH)*0.5f)
                                        .size(pillW, pillH)
                                        .text(statusTxt)
                                        .fontSize(9.5f)
                                        .color(statusFg)
                                        .horizontalAlign(eui::HorizontalAlign::Center)
                                        .verticalAlign(eui::VerticalAlign::Center)
                                        .build();
                                }
                            }

                            // 4) 原文：wrap(true) 完整换行；跳过态降色
                            {
                                int origLines = estimateWrappedLines(e.original, leftW, origFont);
                                float origBoxH = static_cast<float>(origLines) * origLineH;
                                sui.text(rid + ".o")
                                    .position(leftX, rowY + 6.0f + methodH)
                                    .size(leftW, origBoxH)
                                    .text(e.original)
                                    .fontSize(origFont)
                                    .lineHeight(origLineH)
                                    .wrap(true)
                                    .color(skipped ? palette::kSkippedText : palette::kTextBody)
                                    .verticalAlign(eui::VerticalAlign::Top)
                                    .build();
                            }

                            // 5) 译文输入框：multiline，按预估行数给高度，完整编辑/显示
                            {
                                int transLines = std::max(1, estimateWrappedLines(
                                    e.translation.empty() ? " " : e.translation,
                                    std::max(80.0f, inW - 20.0f), transFont));
                                float transBoxH = static_cast<float>(transLines) * transLineH + 10.0f;
                                sui.stack(rid + ".iw")
                                    .position(inX, rowY + (rowH - transBoxH) * 0.5f)
                                    .size(inW, transBoxH)
                                    .content([&] {
                                        components::input(sui, rid + ".t")
                                            .size(inW, transBoxH)
                                            .value(e.translation)
                                            .placeholder(untr ? "未翻译，请输入译文" : "（译文）")
                                            .inset(9.0f)
                                            .fontSize(transFont)
                                            .multiline()
                                            .onChange([&e](const std::string& v){
                                                e.translation=v; e.edited=true;
                                                g_state.statusText = "已编辑译文";
                                            })
                                            .build();
                                    })
                                    .build();
                            }

                            rowY += rowH + rowGap;
                        }
                    })
                    .build();
            })
            .build();

        // ---- 底栏（统计左对齐 + 操作右对齐，按钮分主次三级）----
        const float botY = H - botH;
        ui.stack("bot").y(botY).size(W, botH).content([&] {
            ui.rect("bot.bg").size(W, botH).color(palette::kElevated).build();
            ui.rect("bot.bd").size(W,1.0f).color(palette::kBorder).build();

            // 左侧统计（与按钮分离，避免被挤压/遮挡）
            ui.text("st").x(24.0f).y((botH-18.0f)*0.5f).size(420.0f,18.0f)
                .text(g_state.statusText.empty()
                      ? ("共 " + std::to_string(total) + " 条 · 已勾选 "
                         + std::to_string(enabledCount)
                         + (visible.size() != static_cast<size_t>(total)
                            ? "  ·  筛选 " + std::to_string(visible.size()) : "")
                         + (editedCount>0 ? "  ·  " + std::to_string(editedCount) + " 待保存" : ""))
                      : g_state.statusText)
                .fontSize(12.0f)
                .color(editedCount>0 && g_state.statusText.empty() ? palette::kUntranslatedTint
                                                                   : palette::kTextMute)
                .verticalAlign(eui::VerticalAlign::Center)
                .build();

            // 右侧操作按钮：tertiary(全选/全不选) | secondary(完成) | primary(保存并导出)
            // 从左到右排列，统一 y 居中
            const float btnY = (botH-32.0f)*0.5f;
            const float bw = 92.0f;   // tertiary
            const float sw = 96.0f;   // secondary
            const float pw = 132.0f;  // primary
            const float gap = 10.0f;
            // 主按钮在最右
            const float pX = W - pw - 24.0f;
            const float sX = pX - gap - sw;
            const float nX = sX - gap - bw;   // 全不选
            const float aX = nX - gap - bw;   // 全选

            // tertiary：全选 / 全不选（ghost/secondary 主题）
            ui.stack("b1").position(aX, btnY).size(bw, 32.0f).content([&] {
                components::button(ui, "btnAll").size(bw,32.0f).text("全选")
                    .fontSize(12.5f)
                    .theme(components::theme::dark(), false)
                    .onClick([&]{ for(auto&x:g_state.entries)x.enabled=true;
                                  g_state.statusText="已全选"; }).build();
            });
            ui.stack("b2").position(nX, btnY).size(bw, 32.0f).content([&] {
                components::button(ui, "btnNone").size(bw,32.0f).text("全不选")
                    .fontSize(12.5f)
                    .theme(components::theme::dark(), false)
                    .onClick([&]{ for(auto&x:g_state.entries)x.enabled=false;
                                  g_state.statusText="已全不选"; }).build();
            });
            // secondary：完成（看完直接过）
            ui.stack("bDone").position(sX, btnY).size(sw, 32.0f).content([&] {
                components::button(ui, "btnDone").size(sw,32.0f).text("完成")
                    .fontSize(13.0f)
                    .theme(components::theme::dark(), false)
                    .onClick([&]{
                        g_state.shouldExport=true;
                        if (!g_outPath.empty() && writeOutput(g_outPath,"applied")) {
                            g_written = true;
                            std::cerr << "[review_gui] 完成，退出\n";
                            std::exit(0);
                        } else { g_state.statusText="导出失败"; g_state.shouldExport=false; }
                    }).build();
            });
            // primary：保存并导出（唯一实心强调色主操作）
            ui.stack("b3").position(pX, btnY).size(pw, 32.0f).content([&] {
                components::button(ui, "btnEx").size(pw,32.0f).text("保存并导出")
                    .fontSize(13.0f)
                    .theme(components::theme::dark(), true)
                    .onClick([&]{
                        g_state.shouldExport=true;
                        // 写文件成功后立即退出：标记 written 防 atexit 重复写，再 exit(0)
                        // exit 会走 C 运行时正常退出流程（EUI-NEO 的 OpenGL 资源由 OS 回收）
                        if (!g_outPath.empty() && writeOutput(g_outPath,"applied")) {
                            g_written = true;
                            std::cerr << "[review_gui] 已导出，退出\n";
                            std::exit(0);
                        } else { g_state.statusText="导出失败"; g_state.shouldExport=false; }
                    }).build();
            });
        });
    });
}

} // namespace app
