const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

// Icon imports
const {
  FaYoutube, FaMusic, FaMicrophone, FaAlignLeft, FaClosedCaptioning,
  FaDesktop, FaCog, FaRocket, FaLightbulb, FaChevronRight,
  FaApple, FaSearch, FaLanguage, FaBolt, FaWifi, FaLayerGroup,
  FaCalendarAlt, FaPlay, FaSlidersH, FaVolumeUp, FaMoon,
  FaChurch, FaGlobeAsia, FaRobot, FaMobileAlt, FaCloud, FaUsers
} = require("react-icons/fa");

// ---------- Helpers ----------

function renderIconSvg(IconComponent, color = "#000000", size = 256) {
  return ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
}

async function iconToBase64Png(IconComponent, color, size = 256) {
  const svg = renderIconSvg(IconComponent, color, size);
  const pngBuffer = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + pngBuffer.toString("base64");
}

// ---------- Color Palette ----------
// "Worship Night" theme — deep dark with warm gold accent
const C = {
  darkBg:    "0D1117",   // near-black
  darkNav:   "161B22",   // dark card
  navy:      "1A2332",   // section bg
  accent:    "E8A838",   // warm gold
  accentDk:  "C4881C",   // darker gold
  white:     "FFFFFF",
  light:     "E6EDF3",   // light text
  muted:     "8B949E",   // muted text
  cardBg:    "21262D",   // card background
  blue:      "58A6FF",   // link/highlight blue
  green:     "3FB950",   // success green
  purple:    "BC8CFF",   // purple accent
  contentBg: "F6F8FA",   // light slide bg
  contentTx: "24292F",   // dark text on light
};

const makeShadow = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.3 });

async function main() {
  let pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "LeaderAtWorship";
  pres.title = "LeaderAtWorship — 敬拜字幕生成與即時投影控制";

  // Pre-render all icons
  const icons = {};
  const iconDefs = [
    ["youtube", FaYoutube, C.accent],
    ["music", FaMusic, C.accent],
    ["mic", FaMicrophone, C.accent],
    ["align", FaAlignLeft, C.accent],
    ["subtitle", FaClosedCaptioning, C.accent],
    ["desktop", FaDesktop, C.accent],
    ["cog", FaCog, C.muted],
    ["rocket", FaRocket, C.accent],
    ["bulb", FaLightbulb, C.accent],
    ["chevron", FaChevronRight, C.accent],
    ["apple", FaApple, C.white],
    ["search", FaSearch, C.blue],
    ["lang", FaLanguage, C.green],
    ["bolt", FaBolt, C.accent],
    ["wifi", FaWifi, C.purple],
    ["layer", FaLayerGroup, C.blue],
    ["calendar", FaCalendarAlt, C.accent],
    ["play", FaPlay, C.accent],
    ["slider", FaSlidersH, C.accent],
    ["volume", FaVolumeUp, C.accent],
    ["moon", FaMoon, C.accent],
    ["church", FaChurch, C.white],
    ["globe", FaGlobeAsia, C.accent],
    ["robot", FaRobot, C.blue],
    ["mobile", FaMobileAlt, C.accent],
    ["cloud", FaCloud, C.blue],
    ["users", FaUsers, C.accent],
  ];
  for (const [name, comp, color] of iconDefs) {
    icons[name] = await iconToBase64Png(comp, `#${color}`);
  }

  // ========================================================================
  // SLIDE 1: COVER
  // ========================================================================
  {
    let s = pres.addSlide();
    s.background = { color: C.darkBg };

    // Accent bar at top
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 10, h: 0.06, fill: { color: C.accent }
    });

    // Church icon
    s.addImage({ data: icons.church, x: 4.5, y: 1.0, w: 1.0, h: 1.0 });

    // Title
    s.addText("LeaderAtWorship", {
      x: 0.5, y: 2.1, w: 9, h: 0.9,
      fontSize: 44, fontFace: "Georgia", color: C.white,
      bold: true, align: "center", margin: 0
    });

    // Subtitle
    s.addText("敬拜字幕生成與即時投影控制工具", {
      x: 0.5, y: 3.0, w: 9, h: 0.6,
      fontSize: 20, fontFace: "Calibri", color: C.muted,
      align: "center", margin: 0
    });

    // Divider line
    s.addShape(pres.shapes.LINE, {
      x: 3.5, y: 3.8, w: 3, h: 0,
      line: { color: C.accent, width: 2 }
    });

    // Tag line
    s.addText("Built with FastAPI  |  Optimized for Apple Silicon", {
      x: 0.5, y: 4.1, w: 9, h: 0.5,
      fontSize: 14, fontFace: "Calibri", color: C.muted,
      align: "center", margin: 0
    });
  }

  // ========================================================================
  // SLIDE 2: 專案簡介
  // ========================================================================
  {
    let s = pres.addSlide();
    s.background = { color: C.contentBg };

    // Header bar
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.darkBg }
    });
    s.addText("專案簡介", {
      x: 0.7, y: 0, w: 8, h: 0.9,
      fontSize: 28, fontFace: "Georgia", color: C.white,
      bold: true, valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0.9, w: 10, h: 0.05, fill: { color: C.accent }
    });

    // Main description
    s.addText("LeaderAtWorship 是一套專為教會敬拜團隊設計的自動化字幕系統。", {
      x: 0.7, y: 1.2, w: 8.6, h: 0.6,
      fontSize: 18, fontFace: "Calibri", color: C.contentTx, margin: 0
    });

    // 3 feature cards
    const cards = [
      { icon: "youtube", title: "自動化處理", desc: "輸入 YouTube 連結\n自動完成全部流程" },
      { icon: "subtitle", title: "智慧歌詞對齊", desc: "多來源歌詞搜尋\n錨點式精確對齊" },
      { icon: "desktop", title: "即時投影控制", desc: "WebSocket 即時同步\n一鍵操控投影畫面" },
    ];

    for (let i = 0; i < 3; i++) {
      const cx = 0.7 + i * 3.05;
      s.addShape(pres.shapes.RECTANGLE, {
        x: cx, y: 2.1, w: 2.8, h: 2.6,
        fill: { color: C.white }, shadow: makeShadow()
      });
      // Accent top bar on card
      s.addShape(pres.shapes.RECTANGLE, {
        x: cx, y: 2.1, w: 2.8, h: 0.06, fill: { color: C.accent }
      });
      s.addImage({ data: icons[cards[i].icon], x: cx + 1.05, y: 2.4, w: 0.7, h: 0.7 });
      s.addText(cards[i].title, {
        x: cx, y: 3.2, w: 2.8, h: 0.5,
        fontSize: 16, fontFace: "Calibri", color: C.contentTx,
        bold: true, align: "center", margin: 0
      });
      s.addText(cards[i].desc, {
        x: cx + 0.2, y: 3.7, w: 2.4, h: 0.9,
        fontSize: 12, fontFace: "Calibri", color: C.muted,
        align: "center", margin: 0
      });
    }
  }

  // ========================================================================
  // SLIDE 3: 系統架構
  // ========================================================================
  {
    let s = pres.addSlide();
    s.background = { color: C.darkBg };

    s.addText("系統架構", {
      x: 0.7, y: 0.3, w: 8, h: 0.7,
      fontSize: 32, fontFace: "Georgia", color: C.white, bold: true, margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: 1.0, w: 1.5, h: 0.04, fill: { color: C.accent }
    });

    // Architecture layers
    const layers = [
      { y: 1.3, label: "Frontend", items: "Jinja2 Templates  |  WebSocket Client  |  Audio Player", color: C.blue },
      { y: 2.2, label: "API Layer", items: "FastAPI REST  |  WebSocket Server  |  Background Tasks", color: C.green },
      { y: 3.1, label: "Services", items: "YouTube DL  |  Demucs  |  Whisper  |  Lyrics  |  Aligner", color: C.accent },
      { y: 4.0, label: "Data", items: "SQLite (aiosqlite)  |  Alembic Migrations  |  File Storage", color: C.purple },
    ];

    for (const layer of layers) {
      // Label box
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.7, y: layer.y, w: 1.8, h: 0.7,
        fill: { color: C.cardBg }
      });
      s.addText(layer.label, {
        x: 0.7, y: layer.y, w: 1.8, h: 0.7,
        fontSize: 14, fontFace: "Calibri", color: layer.color,
        bold: true, align: "center", valign: "middle", margin: 0
      });

      // Content box
      s.addShape(pres.shapes.RECTANGLE, {
        x: 2.7, y: layer.y, w: 6.6, h: 0.7,
        fill: { color: C.navy }
      });
      s.addText(layer.items, {
        x: 2.9, y: layer.y, w: 6.4, h: 0.7,
        fontSize: 13, fontFace: "Calibri", color: C.light,
        valign: "middle", margin: 0
      });

      // Accent left border
      s.addShape(pres.shapes.RECTANGLE, {
        x: 2.7, y: layer.y, w: 0.06, h: 0.7,
        fill: { color: layer.color }
      });
    }

    // Bottom note
    s.addText("Apple Silicon 最佳化：MPS 自動偵測 + mlx-whisper 本地推論", {
      x: 0.7, y: 5.0, w: 8.6, h: 0.4,
      fontSize: 11, fontFace: "Calibri", color: C.muted, margin: 0
    });
  }

  // ========================================================================
  // SLIDE 4: PIPELINE 流程
  // ========================================================================
  {
    let s = pres.addSlide();
    s.background = { color: C.contentBg };

    // Header bar
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.darkBg }
    });
    s.addText("Pipeline 處理流程", {
      x: 0.7, y: 0, w: 8, h: 0.9,
      fontSize: 28, fontFace: "Georgia", color: C.white,
      bold: true, valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0.9, w: 10, h: 0.05, fill: { color: C.accent }
    });

    // 6-step pipeline
    const steps = [
      { icon: "youtube", label: "YouTube\n下載", desc: "yt-dlp" },
      { icon: "music",   label: "人聲\n分離", desc: "Demucs" },
      { icon: "mic",     label: "語音\n轉錄", desc: "mlx-whisper" },
      { icon: "search",  label: "歌詞\n搜尋", desc: "多來源 API" },
      { icon: "align",   label: "錨點\n對齊", desc: "DP 演算法" },
      { icon: "subtitle",label: "字幕\n生成", desc: "SRT / VTT" },
    ];

    const startX = 0.5;
    const stepW = 1.3;
    const gap = 0.25;

    for (let i = 0; i < steps.length; i++) {
      const cx = startX + i * (stepW + gap);

      // Step card
      s.addShape(pres.shapes.RECTANGLE, {
        x: cx, y: 1.4, w: stepW, h: 2.8,
        fill: { color: C.white }, shadow: makeShadow()
      });

      // Step number
      s.addShape(pres.shapes.OVAL, {
        x: cx + 0.4, y: 1.6, w: 0.5, h: 0.5,
        fill: { color: C.accent }
      });
      s.addText(String(i + 1), {
        x: cx + 0.4, y: 1.6, w: 0.5, h: 0.5,
        fontSize: 16, fontFace: "Calibri", color: C.white,
        bold: true, align: "center", valign: "middle", margin: 0
      });

      // Icon
      s.addImage({ data: icons[steps[i].icon], x: cx + 0.35, y: 2.3, w: 0.6, h: 0.6 });

      // Label
      s.addText(steps[i].label, {
        x: cx, y: 3.0, w: stepW, h: 0.7,
        fontSize: 13, fontFace: "Calibri", color: C.contentTx,
        bold: true, align: "center", valign: "top", margin: 0
      });

      // Description
      s.addText(steps[i].desc, {
        x: cx, y: 3.7, w: stepW, h: 0.4,
        fontSize: 10, fontFace: "Calibri", color: C.muted,
        align: "center", margin: 0
      });

      // Arrow between steps
      if (i < steps.length - 1) {
        s.addImage({
          data: icons.chevron,
          x: cx + stepW + 0.02, y: 2.65, w: 0.22, h: 0.22
        });
      }
    }

    // Bottom note
    s.addText("Pipeline 支援並行處理 — 多首歌曲可同時在不同階段執行（per-stage semaphores）", {
      x: 0.5, y: 4.6, w: 9, h: 0.5,
      fontSize: 12, fontFace: "Calibri", color: C.muted, margin: 0
    });
  }

  // ========================================================================
  // SLIDES 5-9: DEMO GIF slides
  // ========================================================================
  const demoSlides = [
    {
      title: "Demo 1：Dashboard + YouTube 提交",
      gif: "01-dashboard-submit-youtube.gif",
      bullets: [
        "開啟 Web 介面首頁 Dashboard",
        "輸入 YouTube 連結（支援各種 URL 格式）",
        "一鍵提交至後台 Pipeline 處理",
        "即時回饋任務 ID 與狀態",
      ],
    },
    {
      title: "Demo 2：Pipeline 處理狀態",
      gif: "02-pipeline-processing-status.gif",
      bullets: [
        "即時追蹤每首歌曲的處理進度",
        "顯示各階段狀態：下載 → 分離 → 轉錄 → 對齊",
        "處理完成後自動生成字幕檔案",
        "支援同時處理多首歌曲",
      ],
    },
    {
      title: "Demo 3：敬拜流程編輯",
      gif: "03-worship-flow-schedule.gif",
      bullets: [
        "建立敬拜流程（Worship Flow）",
        "從歌曲庫中選擇並排序歌曲",
        "拖拽調整播放順序",
        "儲存流程供投影使用",
      ],
    },
    {
      title: "Demo 4：歌詞投影顯示",
      gif: "04-projection-lyrics-display.gif",
      bullets: [
        "全螢幕黑底投影模式",
        "5 行滑動視窗歌詞顯示",
        "當前行高亮，上下文淡出",
        "支援中英文歌詞顯示",
      ],
    },
    {
      title: "Demo 5：控制台操作",
      gif: "05-controller-operations.gif",
      bullets: [
        "上/下一行、上/下一首導航",
        "黑幕切換（禱告時使用）",
        "音訊播放：原聲/人聲/伴奏",
        "即時字幕列表與手動輸入",
      ],
    },
  ];

  for (const demo of demoSlides) {
    let s = pres.addSlide();
    s.background = { color: C.darkBg };

    // Title
    s.addText(demo.title, {
      x: 0.7, y: 0.3, w: 8.6, h: 0.7,
      fontSize: 26, fontFace: "Georgia", color: C.white,
      bold: true, margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: 1.0, w: 1.5, h: 0.04, fill: { color: C.accent }
    });

    // GIF placeholder box (left side)
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: 1.3, w: 4.8, h: 3.6,
      fill: { color: C.navy },
      line: { color: C.muted, width: 1, dashType: "dash" }
    });
    s.addText([
      { text: "GIF Demo", options: { fontSize: 16, bold: true, color: C.muted, breakLine: true } },
      { text: demo.gif, options: { fontSize: 11, color: C.muted } },
    ], {
      x: 0.7, y: 1.3, w: 4.8, h: 3.6,
      align: "center", valign: "middle", margin: 0
    });

    // Bullets (right side)
    const bulletItems = demo.bullets.map((b, i) => ({
      text: b,
      options: {
        bullet: true,
        breakLine: i < demo.bullets.length - 1,
        fontSize: 14,
        fontFace: "Calibri",
        color: C.light,
        paraSpaceAfter: 10,
      }
    }));
    s.addText(bulletItems, {
      x: 5.8, y: 1.5, w: 3.8, h: 3.2,
      valign: "top", margin: 0
    });

    // Bottom note
    s.addText("插入對應 GIF 動畫以呈現實際操作效果", {
      x: 0.7, y: 4.9, w: 8.3, h: 0.4,
      fontSize: 10, fontFace: "Calibri", color: C.muted,
      italic: true, margin: 0
    });
  }

  // ========================================================================
  // SLIDE 10: 技術亮點
  // ========================================================================
  {
    let s = pres.addSlide();
    s.background = { color: C.contentBg };

    // Header bar
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 10, h: 0.9, fill: { color: C.darkBg }
    });
    s.addText("技術亮點", {
      x: 0.7, y: 0, w: 8, h: 0.9,
      fontSize: 28, fontFace: "Georgia", color: C.white,
      bold: true, valign: "middle", margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0.9, w: 10, h: 0.05, fill: { color: C.accent }
    });

    // 2x3 grid of tech highlights
    const techs = [
      { icon: "apple", title: "Apple Silicon 優化", desc: "MPS 自動偵測 GPU\nmlx-whisper 本地推論", bg: C.darkBg },
      { icon: "globe", title: "多來源歌詞搜尋", desc: "Tencent · NetEase\nMusixmatch · LRCLIB", bg: C.darkBg },
      { icon: "lang", title: "繁簡轉換", desc: "OpenCC s2twp\n簡體自動轉繁體台灣用詞", bg: C.darkBg },
      { icon: "bolt", title: "錨點式 DP 對齊", desc: "RapidFuzz 模糊匹配\n動態規劃最佳路徑", bg: C.darkBg },
      { icon: "wifi", title: "WebSocket 即時同步", desc: "顯示端 + 控制端\n延遲 < 50ms", bg: C.darkBg },
      { icon: "layer", title: "Pipeline 並行", desc: "Per-stage Semaphore\n多首歌同時處理", bg: C.darkBg },
    ];

    for (let row = 0; row < 2; row++) {
      for (let col = 0; col < 3; col++) {
        const i = row * 3 + col;
        const cx = 0.5 + col * 3.1;
        const cy = 1.2 + row * 2.0;

        s.addShape(pres.shapes.RECTANGLE, {
          x: cx, y: cy, w: 2.85, h: 1.75,
          fill: { color: techs[i].bg }, shadow: makeShadow()
        });

        s.addImage({ data: icons[techs[i].icon.replace("#", "")], x: cx + 0.2, y: cy + 0.2, w: 0.45, h: 0.45 });

        s.addText(techs[i].title, {
          x: cx + 0.75, y: cy + 0.2, w: 1.9, h: 0.45,
          fontSize: 14, fontFace: "Calibri", color: C.white,
          bold: true, valign: "middle", margin: 0
        });
        s.addText(techs[i].desc, {
          x: cx + 0.2, y: cy + 0.8, w: 2.45, h: 0.8,
          fontSize: 11, fontFace: "Calibri", color: C.muted,
          margin: 0
        });
      }
    }
  }

  // ========================================================================
  // SLIDE 11: 未來規劃
  // ========================================================================
  {
    let s = pres.addSlide();
    s.background = { color: C.darkBg };

    s.addText("未來規劃", {
      x: 0.7, y: 0.3, w: 8, h: 0.7,
      fontSize: 32, fontFace: "Georgia", color: C.white, bold: true, margin: 0
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.7, y: 1.0, w: 1.5, h: 0.04, fill: { color: C.accent }
    });

    const plans = [
      { icon: "robot", title: "AI 歌詞校正", desc: "利用 LLM 自動修正 Whisper 轉錄錯誤，提升字幕品質" },
      { icon: "mobile", title: "行動裝置控制", desc: "手機瀏覽器即可操控投影，無需額外安裝 App" },
      { icon: "cloud", title: "雲端歌詞庫", desc: "建立教會共享歌詞資料庫，一次校正全教會受益" },
      { icon: "users", title: "多螢幕支援", desc: "支援多個投影螢幕同時輸出，適應大型聚會場景" },
    ];

    for (let i = 0; i < plans.length; i++) {
      const cy = 1.3 + i * 1.0;

      // Icon circle
      s.addShape(pres.shapes.OVAL, {
        x: 0.7, y: cy, w: 0.65, h: 0.65,
        fill: { color: C.cardBg }
      });
      s.addImage({ data: icons[plans[i].icon], x: 0.82, y: cy + 0.12, w: 0.4, h: 0.4 });

      // Title
      s.addText(plans[i].title, {
        x: 1.6, y: cy, w: 3.0, h: 0.35,
        fontSize: 16, fontFace: "Calibri", color: C.white,
        bold: true, valign: "middle", margin: 0
      });
      // Description
      s.addText(plans[i].desc, {
        x: 1.6, y: cy + 0.35, w: 7.5, h: 0.35,
        fontSize: 12, fontFace: "Calibri", color: C.muted,
        valign: "top", margin: 0
      });
    }
  }

  // ========================================================================
  // SLIDE 12: 結語
  // ========================================================================
  {
    let s = pres.addSlide();
    s.background = { color: C.darkBg };

    // Accent bar at bottom
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 5.565, w: 10, h: 0.06, fill: { color: C.accent }
    });

    // Church icon
    s.addImage({ data: icons.church, x: 4.5, y: 1.2, w: 1.0, h: 1.0 });

    s.addText("Thank You", {
      x: 0.5, y: 2.4, w: 9, h: 0.8,
      fontSize: 40, fontFace: "Georgia", color: C.white,
      bold: true, align: "center", margin: 0
    });

    s.addText("讓科技服事敬拜，讓敬拜更加專注", {
      x: 0.5, y: 3.2, w: 9, h: 0.6,
      fontSize: 20, fontFace: "Calibri", color: C.accent,
      align: "center", margin: 0
    });

    // Divider
    s.addShape(pres.shapes.LINE, {
      x: 3.5, y: 4.1, w: 3, h: 0,
      line: { color: C.muted, width: 1 }
    });

    s.addText("github.com/PH-SHIH/LeaderAtWorship", {
      x: 0.5, y: 4.3, w: 9, h: 0.5,
      fontSize: 14, fontFace: "Calibri", color: C.muted,
      align: "center", margin: 0
    });
  }

  // ========================================================================
  // WRITE FILE
  // ========================================================================
  const outPath = "/Users/shibangxin/Documents/GitHub/LeaderAtWorship/.claude/worktrees/practical-lichterman/docs/LeaderAtWorship-Demo.pptx";
  await pres.writeFile({ fileName: outPath });
  console.log("Presentation written to: " + outPath);
}

main().catch(e => { console.error(e); process.exit(1); });
