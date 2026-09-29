const {
    By,
    until
} = require("selenium-webdriver");


class HomePage {

    constructor(driver) {

        this.driver = driver;


        // ==============================
        // 首页地址
        // ==============================

        this.url =
            "http://127.0.0.1:5173/";


        // ==============================
        // 首页主要标题
        // ==============================

        this.mainTitle =
            By.xpath(
                '//*[contains(normalize-space(.), "根据你的职业")]'
            );


        // “推荐最适合的资源”
        this.recommendTitle =
            By.xpath(
                '//*[contains(normalize-space(.), "推荐最适合")]'
            );


        // ==============================
        // 顶部导航
        // ==============================

        this.homeNav =
            By.xpath(
                '//*[normalize-space(.)="首页"]'
            );


        this.favoriteNav =
            By.xpath(
                '//*[normalize-space(.)="收藏"]'
            );


        this.aiNav =
            By.xpath(
                '//*[normalize-space(.)="AI助手"]'
            );


        // ==============================
        // 搜索框
        // ==============================

        this.searchInput =
            By.css(
                'input[placeholder*="搜索工具"]'
            );


        // ==============================
        // 搜索类型
        // ==============================

        this.searchType =
            By.xpath(
                '//*[normalize-space(.)="站内搜索"]'
            );

    }


    // ==================================================
    // 找到真正可见的元素
    // 防止 Vue 页面里出现隐藏的重复节点
    // ==================================================

    async getVisibleElement(
        locator,
        timeout = 10000
    ) {

        return await this.driver.wait(

            async () => {

                const elements =
                    await this.driver.findElements(
                        locator
                    );


                for (const element of elements) {

                    try {

                        if (
                            await element.isDisplayed()
                        ) {

                            return element;
                        }

                    } catch (error) {

                        // 元素失效时继续寻找
                    }

                }


                return false;

            },

            timeout,

            "没有找到可见元素"

        );

    }


    // ==============================
    // 等待首页加载完成
    // ==============================

    async waitForLoaded() {

        await this.driver.wait(

            async () => {

                const currentUrl =
                    await this.driver
                        .getCurrentUrl();


                return !currentUrl.includes(
                    "/login"
                );

            },

            10000,

            "首页加载失败，仍然停留在登录页"

        );


        await this.getVisibleElement(
            this.mainTitle
        );

    }


    // ==============================
    // 获取当前 URL
    // ==============================

    async getCurrentUrl() {

        return await this.driver
            .getCurrentUrl();

    }


    // ==============================
    // 首页主标题是否显示
    // ==============================

    async isMainTitleVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.mainTitle
                );


            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 推荐标题是否显示
    // ==============================

    async isRecommendTitleVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.recommendTitle
                );


            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 首页导航是否显示
    // ==============================

    async isHomeNavVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.homeNav
                );


            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 收藏导航是否显示
    // ==============================

    async isFavoriteNavVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.favoriteNav
                );


            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // AI助手导航是否显示
    // ==============================

    async isAINavVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.aiNav
                );


            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 搜索框是否显示
    // ==============================

    async isSearchInputVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.searchInput
                );


            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 站内搜索选项是否显示
    // ==============================

    async isSearchTypeVisible() {

        try {

            const element =
                await this.getVisibleElement(
                    this.searchType
                );


            return await element.isDisplayed();

        } catch (error) {

            return false;
        }

    }


    // ==============================
    // 刷新首页
    // ==============================

    async refresh() {

        await this.driver.navigate()
            .refresh();


        await this.waitForLoaded();

    }

}


module.exports = HomePage;