"use client"

import { AuroraBackground } from "@/components/aurora-background"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { BookOpen, Users, Sparkles, ArrowUpRight, Clock, Mail } from "lucide-react"
import Link from "next/link"
import { NavBar } from "@/components/nav-bar"
import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision"
import { motion, useScroll, useTransform } from "framer-motion"
import { useRef, useState, useEffect } from "react"
import { HyperText } from "@/components/ui/hyper-text"
import { fetchLatestPapers, type Paper, translatePaper } from "@/services/api"

export default function Home() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start start", "end start"]
  });

  // 两个页面使用相同的进度区间 [0, 0.5]，实现同步动画
  const firstPageY = useTransform(scrollYProgress, [0, 0.5], ["0%", "-100%"]);
  const firstPageOpacity = useTransform(scrollYProgress, [0, 0.5], [1, 0]);
  const firstPageScale = useTransform(scrollYProgress, [0, 0.5], [1, 0.8]);
  const firstPageRotate = useTransform(scrollYProgress, [0, 0.5], [0, 20]);

  // 第二页同步上移
  const secondPageY = useTransform(scrollYProgress, [0, 0.5], ["100%", "0%"]);
  const secondPageOpacity = useTransform(scrollYProgress, [0, 0.5], [0, 1]);
  const secondPageScale = useTransform(scrollYProgress, [0, 0.5], [0.8, 1]);

  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedCategory, setSelectedCategory] = useState("cs.AI");
  const [isLoading, setIsLoading] = useState(true);
  const [translatingIds, setTranslatingIds] = useState<Set<string>>(new Set());

  const categories = [
    { value: "cs.AI", label: "人工智能" },
    { value: "cs.LG", label: "机器学习" },
    { value: "cs.CV", label: "计算机视觉" },
    { value: "cs.CL", label: "计算语言学" },
    { value: "cs.RO", label: "机器人" },
    // { value: "cs.NE", label: "神经网络" },
    // { value: "cs.OS", label: "操作系统" },
    // { value: "cs.SE", label: "软件工程" },
    // { value: "econ.TH", label: "经济学理论" },
    // { value: "math.PR", label: "概率论" },
    // { value: "math.NT", label: "数论" },
    // { value: "math.IT", label: "信息论" },
    // { value: "physics.app-ph", label: "应用物理" },
    // { value: "q-bio.GN", label: "基因组学" },
    { value: "stat.ML", label: "统计机器学习" },
    // { value: "astro-ph.HE", label: "天文学" },
  ];

  useEffect(() => {
    const loadPapers = async () => {
      setIsLoading(true);
      try {
        const data = await fetchLatestPapers(selectedCategory);
        setPapers(data);
      } catch (error) {
        console.error("Failed to fetch papers:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadPapers();
  }, [selectedCategory]);

  return (
    <div ref={containerRef} className="h-[200vh] relative overflow-hidden">
      {/* Hero Section */}
      <motion.section 
        className="h-screen fixed top-0 left-0 w-full"
        style={{ 
          y: firstPageY,
          opacity: firstPageOpacity,
          scale: firstPageScale,
          rotateX: firstPageRotate,
          transformPerspective: "1000px"
        }}
      >
        <AuroraBackground className="h-screen w-full">
          <div className="relative z-50 w-full">
            <NavBar />
          </div>
          <div className="z-10 flex flex-col items-center gap-4 sm:gap-12 px-2 sm:px-4 text-center pt-8 sm:pt-32">
            <div className="space-y-3 sm:space-y-8">
              <HyperText
                text="Stay Updated with arXiv"
                className="text-3xl sm:text-7xl font-bold tracking-tight text-gray-800"
                duration={1100}
                animateOnLoad={true}
              />
              <p className="text-base sm:text-2xl text-gray-600 max-w-3xl mx-auto px-2">
                The fastest way to track research topics and trends that matter to you
              </p>
              <div className="flex gap-3 sm:gap-6 justify-center">
                <Link href="/subscribe">
                  <Button size="default" className="text-sm sm:text-xl gap-1.5 sm:gap-2 px-3 sm:px-8 py-2 sm:py-6 bg-emerald-500 hover:bg-emerald-600 text-white">
                    Get Started
                    <ArrowUpRight className="w-3 h-3 sm:w-5 sm:h-5" />
                  </Button>
                </Link>
              </div>
            </div>

            {/* 统计数据 */}
            <div className="grid grid-cols-2 gap-2 sm:gap-8 mt-4 sm:mt-16 w-full max-w-4xl px-2">
              {[
                { icon: BookOpen, label: "Multi Domain" },
                { icon: Users, label: "Free Access" },
                { icon: Sparkles, label: "AI Curated" },
                { icon: Mail, label: "Daily Update" },
              ].map((item, i) => (
                <div
                  key={i}
                  className="flex flex-col items-center gap-1 sm:gap-4 p-2 sm:p-8 rounded-xl bg-background/50 backdrop-blur-sm hover:bg-background/60 transition-colors"
                >
                  <item.icon className="w-6 h-6 sm:w-12 sm:h-12 text-primary" />
                  <span className="font-semibold text-sm sm:text-2xl text-gray-800">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </AuroraBackground>
      </motion.section>

      {/* Latest Papers Section */}
      <motion.section
        className="h-screen fixed top-0 left-0 w-full bg-gray-50 overflow-hidden"
        style={{
          y: secondPageY,
          opacity: secondPageOpacity,
          scale: secondPageScale,
        }}
      >
        <div className="relative z-50">
          <NavBar />
        </div>
        <BackgroundBeamsWithCollision 
          className="!fixed !inset-0 !w-screen !h-screen" 
          style={{zIndex: 0}}
        >
          <></>
        </BackgroundBeamsWithCollision>
        {/* 添加装饰性背景 */}
        <div className="absolute top-1/5 right-0 w-1/3 h-full">
          <div className="absolute top-[-20%] right-[-20%] w-full h-[140%] bg-emerald-400/10 rounded-l-full" />
        </div>
        
        <div className="relative z-10 w-full h-full px-4 py-14 overflow-y-auto">
          <div className="max-w-7xl mx-auto">
            <div className="text-center mb-8">
              <h1 className="text-2xl sm:text-5xl font-bold mb-2 sm:mb-4 relative z-20">Latest Papers</h1>
              <p className="text-base sm:text-2xl text-muted-foreground max-w-3xl mx-auto relative z-20 px-2 mb-6">
                Stay up to date with the newest research in your field
              </p>
              
              {/* 类别选择导航栏 */}
              <div className="flex justify-center mb-8">
                <Tabs 
                  value={selectedCategory} 
                  onValueChange={setSelectedCategory}
                  className="w-full max-w-3xl"
                >
                  <TabsList className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                    {categories.map((category) => (
                      <TabsTrigger
                        key={category.value}
                        value={category.value}
                        className="px-3 py-2 text-sm sm:text-base"
                      >
                        {category.label}
                      </TabsTrigger>
                    ))}
                  </TabsList>
                </Tabs>
              </div>
            </div>

            {/* 论文列表 */}
            <div className="grid grid-cols-1 gap-4 sm:gap-6">
              {isLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-t-emerald-500 border-emerald-200"></div>
                </div>
              ) : papers.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No papers found in this category
                </div>
              ) : (
                papers.map((paper) => (
                  <Card key={paper.entry_id} className="p-4 sm:p-6 hover:shadow-lg transition-shadow">
                    <div className="mb-3 sm:mb-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="default" className="text-sm bg-blue-600 hover:bg-blue-700 text-white">
                          {paper.category}
                        </Badge>
                        <Badge variant="outline" className="text-sm bg-amber-50 text-amber-600 border-amber-200">
                          New
                        </Badge>
                      </div>
                    </div>
                    <h3 className="text-lg sm:text-xl font-bold mb-2 text-gray-900">{paper.title}</h3>
                    <p className="text-sm sm:text-base text-gray-600 mb-4">
                      {paper.abstract}
                    </p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 sm:gap-4 text-gray-500 text-sm sm:text-base">
                        <div className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          <span>
                            {new Date(paper.publishedAt).toLocaleString('zh-CN', {
                              year: 'numeric',
                              month: '2-digit',
                              day: '2-digit',
                              hour: '2-digit',
                              minute: '2-digit',
                              hour12: false
                            })}
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button 
                          variant="outline" 
                          size="lg"
                          onClick={async () => {
                            try {
                              // 设置翻译中状态
                              setTranslatingIds(prev => new Set(prev).add(paper.entry_id));
                              const translatedPaper = await translatePaper(paper.entry_id);
                              // 更新papers数组中对应的文章
                              setPapers(papers.map(p => 
                                p.entry_id === paper.entry_id ? translatedPaper : p
                              ));
                            } catch (error) {
                              console.error('Translation failed:', error);
                            } finally {
                              // 移除翻译中状态
                              setTranslatingIds(prev => {
                                const newSet = new Set(prev);
                                newSet.delete(paper.entry_id);
                                return newSet;
                              });
                            }
                          }}
                          disabled={translatingIds.has(paper.entry_id)}
                          className="text-xs sm:text-sm text-blue-600 border-blue-300 hover:bg-blue-50 hover:text-blue-700"
                        >
                          {translatingIds.has(paper.entry_id) ? (
                            <div className="inline-block animate-spin rounded-full h-4 w-4 border-2 border-t-blue-500 border-blue-200"></div>
                          ) : (
                            'translate'
                          )}
                        </Button>
                        <Link 
                          href={paper.entry_id} 
                          target="_blank" 
                          rel="noopener noreferrer"
                        >
                          <Button 
                            variant="outline" 
                            size="lg" 
                            className="text-xs sm:text-sm text-emerald-600 border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700"
                          >
                            Read
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>
        </div>
      </motion.section>

    </div>
  )
}

