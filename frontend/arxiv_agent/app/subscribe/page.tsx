"use client"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Mail, Plus, X } from "lucide-react"
import { useState, useEffect, useRef } from "react"
import { NavBar } from "@/components/nav-bar"
import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { submitSearchRequest, sendSubscribeSuccessEmail } from '@/services/api'
import { Alert } from "@/components/ui/alert"
import { CircleCheck } from "lucide-react"

// 主题标签数据
const TOPICS = [
  "人工智能",
  // "cs.AR(硬件架构)",
  // "cs.CC(计算复杂性)",
  // "cs.CE(计算工程、金融和科学)",
  // "cs.CG(计算几何)",
  // "cs.CL(计算语言学)",
  "计算机视觉",
  // "cs.CY(计算与语言)",
  // "cs.DB(数据库)",
  // "cs.DC(分布式、并行和集群计算)",
  // "cs.DL(数字图书馆)",
  // "cs.DM(离散数学)",
  // "cs.DS(数据结构与算法)",
  // "cs.ET(新兴技术)",
  // "cs.FL(形式语言与自动机理论)",
  // "cs.GL(一般文献)",
  // "cs.GT(计算机图形学)",
  // "cs.HC(人机交互)",
  // "cs.IR(信息检索)",
  // "cs.IT(信息论)",
  "机器学习",
  "统计机器学习",
  // "cs.LO(计算机科学中的逻辑)",
  // "cs.MA(机器学习)",
  // "cs.MM(机器学习)",
  // "cs.NE(机器学习)",
  // "cs.NI(网络与互联网架构)",
  // "cs.OH(其他计算机科学)",
  "计算语言学",
  // "cs.PL(编程语言)",
  "机器人",
  // "cs.SC(科学计算)",
  // "cs.SD(软件工程)",
  // "cs.SE(软件工程)",
  // "cs.SI(社会和信息系统)",
  // "cs.SY(系统与控制)",
  // "econ.EM(计量经济学)",
  // "econ.GN(一般经济学)",
  // "econ.TH(理论经济学)",
  // "eess.AS(音频和语音处理)",
  // "eess.IV(图像和视频处理)",
  // "eess.SP(信号处理)",
  // "eess.SY(系统与控制)",
  // "math.AC(交换代数)",
  // "math.AG(代数几何)",
  // "math.AP(分析与偏微分方程)",
  // "math.AT(代数拓扑)",
  // "math.CA(经典分析与ODEs)",
  // "math.CO(组合学)",
  // "math.CT(范畴论)",
  // "math.CV(复变函数)",
  // "math.DG(微分几何)",
  // "math.DS(动力系统)",
  // "math.FA(泛函分析)",
  // "math.GM(一般数学)",
  // "math.GN(一般拓扑)",
  // "math.GR(群论)",
  // "math.HO(数学史与概述)",
  // "math.IT(信息论)",
  // "math.KT(K理论和同调)",
  // "math.LO(逻辑)",
  // "math.MG(度量几何)",
  // "math.MP(数学物理)",
  // "math.NA(数值分析)",
  // "math.NT(数论)",
  // "math.OA(算子代数)",
  // "math.OC(优化与控制)",
  // "math.PR(概率论)",
  // "math.QA(量子代数)",
  // "math.RA(环与代数)",
  // "math.RT(表示论)",
  // "math.SG(辛几何)",
  // "math.SP(谱理论)",
  // "math.ST(统计理论)",
  // "physics.acc-ph(加速器物理)",
  // "physics.ao-ph(大气和海洋物理)",
  // "physics.app-ph(应用物理)",
  // "physics.atm-clus(原子和分子团簇)",
  // "physics.atom-ph(原子物理)",
  // "physics.bio-ph(生物物理)",
  // "physics.chem-ph(化学物理)",
  // "physics.class-ph(经典物理)",
  // "physics.comp-ph(计算物理)",
  // "physics.data-an(数据分析、统计和概率)",
  // "physics.ed-ph(物理教育)",
  // "physics.flu-dyn(流体动力学)",
  // "physics.gen-ph(一般物理)",
  // "physics.geo-ph(地球物理)",
  // "physics.hist-ph(物理史)",
  // "physics.ins-det(仪器和探测器)",
  // "physics.med-ph(医学物理)",
  // "physics.optics(光学)",
  // "physics.plasm-ph(等离子体物理)",
  // "physics.pop-ph(大众物理)",
  // "physics.soc-ph(社会物理和社会经济系统)",
  // "physics.space-ph(空间物理)",
  // "q-bio.BM(生物分子)",
  // "q-bio.CB(细胞行为)",
  // "q-bio.GN(基因组学)",
  // "q-bio.MN(分子网络)",
  // "q-bio.NC(神经元与认知)",
  // "q-bio.OT(其他定量生物学)",
  // "q-bio.PE(种群与进化)",
  // "q-bio.QM(定量方法)",
  // "q-bio.SC(亚细胞过程)",
  // "q-bio.TO(组织与器官)",
  // "q-fin.CP(计算金融)",
  // "q-fin.EC(经济学)",
  // "q-fin.GN(一般金融)",
  // "q-fin.MF(数学金融)",
  // "q-fin.PM(投资组合管理)",
  // "q-fin.PR(证券定价)",
  // "q-fin.RM(风险管理)",
  // "q-fin.ST(统计金融)",
  // "q-fin.TR(交易和市场微观结构)",
  // "stat.AP(应用统计)",
  // "stat.CO(计算统计)",
  // "stat.ME(方法论)",
  // "stat.ML(机器学习)",
  // "stat.OT(其他统计)",
  // "stat.TH(统计理论)",
  // "hep-ex(高能物理实验)",
  // "hep-lat(格点场论)",
  // "hep-ph(高能物理现象学)",
  // "hep-th(高能物理理论)",
  // "nucl-ex(核物理实验)",
  // "nucl-th(核物理理论)",
  // "nlin.AO(适应和自组织)",
  // "nlin.CD(混沌动力学)",
  // "nlin.CG(细胞自动机和格气)",
  // "nlin.PS(图案形成和孤子)",
  // "nlin.SI(完全可积系统)",
  // "quant-ph(量子物理)",
  // "astro-ph.CO(宇宙学和银河系外天文学)",
  // "astro-ph.EP(地球和行星天体物理学)",
  // "astro-ph.GA(银河系天体物理学)",
  // "astro-ph.HE(高能天体物理现象)",
  // "astro-ph.IM(仪器和方法)",
  // "astro-ph.SR(太阳和恒星天体物理学)",
  // "cond-mat.dis-nn(无序系统和神经网络)",
  // "cond-mat.mes-hall(介观系统和量子霍尔效应)",
  // "cond-mat.mtrl-sci(材料科学)",
  // "cond-mat.other(其他凝聚态物理)",
  // "cond-mat.quant-gas(量子气体)",
  // "cond-mat.soft(软凝聚态物理)",
  // "cond-mat.stat-mech(统计力学)",
  // "cond-mat.str-el(强关联电子系统)",
  // "cond-mat.supr-con(超导)",
]

// 添加类型定义
type TopicDict = {
  [key: string]: string;
  "人工智能": "cs.AI";
  "计算机视觉": "cs.CV";
  "机器学习": "cs.LG";
  "统计机器学习": "stat.ML";
  "计算语言学": "cs.CL";
  "机器人": "cs.RO";
}

// 使用类型断言定义 TOPICS_DICT
const TOPICS_DICT: TopicDict = {
  "人工智能": "cs.AI",
  "计算机视觉": "cs.CV",
  "机器学习": "cs.LG",
  "统计机器学习": "stat.ML",
  "计算语言学": "cs.CL",
  "机器人": "cs.RO",
} as const;

export default function Subscribe() {
  const [email, setEmail] = useState("")
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [hour, setHour] = useState("09")
  const [minute, setMinute] = useState("00")
  const [showTopics, setShowTopics] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [showAlert, setShowAlert] = useState(false);

  // 生成小时选项
  const hours = Array.from({ length: 24 }, (_, i) => i.toString().padStart(2, '0'))
  // 生成分钟选项 (每15分钟)
  const minutes = Array.from({ length: 4 }, (_, i) => (i * 15).toString().padStart(2, '0'))

  // 添加内容高度状态和引用
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState("150vh");

  // 监听内容高度变化
  useEffect(() => {
    const updateHeight = () => {
      if (contentRef.current) {
        const height = contentRef.current.scrollHeight;
        setContentHeight(`${height}px`);
      }
    };

    // 初始更新
    updateHeight();

    // 监听窗口大小变化
    window.addEventListener('resize', updateHeight);
    
    // 监听内容变化（当显示/隐藏主题列表时）
    const observer = new MutationObserver(updateHeight);
    if (contentRef.current) {
      observer.observe(contentRef.current, {
        childList: true,
        subtree: true,
        attributes: true
      });
    }

    return () => {
      window.removeEventListener('resize', updateHeight);
      observer.disconnect();
    };
  }, [showTopics]); // 当显示/隐藏主题列表时重新计算

  const handleSubscribe = async () => {
    if (email && selectedTopics.length > 0) {
      try {
        const pushTime = `${hour}:${minute}`;
        
        // 使用类型断言确保 topic 是 TOPICS_DICT 的有效键
        const topicCodes = selectedTopics.map(topic => TOPICS_DICT[topic as keyof TopicDict]);
        
        // 提交订阅请求
        const response = await submitSearchRequest({
          email,
          topics: topicCodes,
          query_content: searchQuery,
          push_time: pushTime
        });

        if (response.status === 'success') {
          // 发送订阅成功邮件
          await sendSubscribeSuccessEmail(email, pushTime);
          
          setShowAlert(true);
          // 3秒后自动关闭提示
          setTimeout(() => setShowAlert(false), 3000);
        }
      } catch (error) {
        console.error('订阅失败:', error);
        alert(error instanceof Error ? error.message : '订阅失败，请重试。');
      }
    }
  };

  const toggleTopic = (topic: string) => {
    if (selectedTopics.includes(topic)) {
        setSelectedTopics(selectedTopics.filter((t) => t !== topic))
    } else {
        // 直接替换当前选择的主题，而不是添加
        setSelectedTopics([topic])
    }
  }

  return (
    <div className="w-full min-h-screen">
      <div className="relative w-full">
        <BackgroundBeamsWithCollision 
          className="absolute top-[16vh] left-0 w-full"
          style={{ height: contentHeight }}
        >  
          <div className="absolute inset-0" />
        </BackgroundBeamsWithCollision>

        <div className="relative z-10" ref={contentRef}>
          <NavBar />
          <div className="content-container px-4 relative z-20 mt-[15vh]">
            <div className="max-w-5xl mx-auto pb-20">
              <div className="text-center mb-12">
                <h1 className="text-4xl sm:text-5xl font-bold mb-6">Research Paper Updates</h1>
                <p className="text-xl sm:text-2xl text-muted-foreground max-w-3xl mx-auto">
                  Select your topics of interest and get personalized research paper recommendations
                </p>
              </div>
              <div className="fixed top-1/5 right-0 w-1/3 h-full z-0">
                <div className="absolute top-[35%] right-[-20%] w-full h-[140%] bg-emerald-400/10 rounded-l-full" />
              </div>
              <div className="space-y-10">
                <div className="flex flex-col gap-6">
                  <div className="space-y-3">
                    <label className="text-xl font-medium">Search Topics</label>
                    <div className="relative max-w-xl" >
                      <Input
                        id="topic-search"
                        placeholder="Search for research topics..."
                        className="w-full"
                        // minHeight={56}
                        // maxHeight={56}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="text-xl font-medium">Selected Topic</label>
                    <div className="flex flex-wrap gap-3">
                        {selectedTopics.map((topic) => (
                            <Badge key={topic} variant="secondary" className="pl-3 py-2 text-lg">
                                {topic}
                                <button onClick={() => toggleTopic(topic)} className="ml-2 hover:text-destructive">
                                    <X className="h-4 w-4" />
                                </button>
                            </Badge>
                        ))}
                        {selectedTopics.length < 1 && (
                            <Button variant="outline" size="lg" onClick={() => setShowTopics(!showTopics)} className="gap-2 text-lg">
                                <Plus className="h-5 w-5" />
                                Add Topic
                            </Button>
                        )}
                    </div>
                    {showTopics && (
                        <Card className="p-6 mt-3 bg-background/80 backdrop-blur-sm">
                            <div className="grid grid-cols-2 gap-3">
                                {TOPICS.filter((topic) => !selectedTopics.includes(topic)).map((topic) => (
                                    <Button
                                        key={topic}
                                        variant="ghost"
                                        className={`justify-start text-lg py-6 ${
                                            selectedTopics.length >= 1 ? 'opacity-50 cursor-not-allowed' : ''
                                        }`}
                                        onClick={() => toggleTopic(topic)}
                                        disabled={selectedTopics.length >= 1}
                                    >
                                        {topic}
                                    </Button>
                                ))}
                            </div>
                        </Card>
                    )}
                  </div>

                  <div className="space-y-3">
                    <label className="text-xl font-medium">Email Address</label>
                    <div className="relative max-w-xl">
                      <Mail className="absolute left-3 top-4 h-6 w-6 text-muted-foreground" />
                      <Input
                        type="email"
                        placeholder="Enter your email for updates"
                        className="pl-12 py-6 text-lg bg-background/80 backdrop-blur-sm"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="space-y-3">
                    <label className="text-xl font-medium">Update Time</label>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2 bg-background/80 backdrop-blur-sm rounded-md p-2">
                        <Select value={hour} onValueChange={setHour}>
                          <SelectTrigger className="w-[100px] text-lg py-5">
                            <SelectValue placeholder="Hour" />
                          </SelectTrigger>
                          <SelectContent>
                            {hours.map((h) => (
                              <SelectItem key={h} value={h}>
                                {h}:00
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        
                        <span className="text-2xl">:</span>
                        
                        <Select value={minute} onValueChange={setMinute}>
                          <SelectTrigger className="w-[100px] text-lg py-5">
                            <SelectValue placeholder="Min" />
                          </SelectTrigger>
                          <SelectContent>
                            {minutes.map((m) => (
                              <SelectItem key={m} value={m}>
                                {m}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <p className="text-lg text-muted-foreground mt-2">
                      Papers will be delivered to your inbox daily at {hour}:{minute}
                    </p>
                  </div>

                  <Button
                    className="w-full text-xl py-8 mt-6 bg-emerald-500 hover:bg-emerald-600 text-white"
                    size="lg"
                    disabled={!email || selectedTopics.length === 0 || !hour || !minute || !searchQuery}
                    onClick={handleSubscribe}
                  >
                    Subscribe to Updates
                  </Button>
                </div>
              </div>
            </div>
          </div>

          {/* 成功提示 Alert */}
          {showAlert && (
            <div className="fixed inset-0 flex items-center justify-center z-50 bg-black/20 backdrop-blur-sm">
              <Alert
                variant="success"
                layout="row"
                isNotification={true}
                className="w-[500px] p-6"
                icon={
                  <CircleCheck 
                    className="text-emerald-500" 
                    size={24}
                    strokeWidth={2} 
                  />
                }
                action={
                  <button 
                    onClick={() => setShowAlert(false)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    <X size={20} />
                  </button>
                }
              >
                <div className="flex flex-col items-center w-full text-center">
                  <h3 className="text-xl font-semibold text-emerald-600 mb-2">
                    订阅成功！
                  </h3>
                  <p className="text-base text-gray-600">
                    您已成功订阅arXivAgent，我们将在每天的{hour}:{minute}为您发送arXiv论文分析报告。
                  </p>
                </div>
              </Alert>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

