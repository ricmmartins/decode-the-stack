---
HEADLINE: AI ambitions meet the realities of production

Wednesday’s reporting connects expanding AI capabilities with the engineering boundaries that make them usable: evaluation, isolation, state management, and infrastructure constraints. Alongside new models and agent integrations, migration accounts and security incidents show why operational evidence matters more than launch claims alone.

## 🧑‍💻 Software Engineering

### [Engineering AI Discover](https://netflixtechblog.com/engineering-ai-discover-e244944cdc38?source=rss----2615bd06b42e---4)
*Netflix’s discovery experiment puts the intelligence layer inside an existing consumer experience.*

Netflix describes AI Discover as a new tab in its TV app where a small group of members can try new ways to find something to watch. Its engineering article focuses on the challenges and decisions behind that feature’s intelligence layer. The limited audience is important context: this is an account of an experiment, not evidence of a broadly deployed replacement for Netflix’s existing discovery experience.

The engineering question is how intelligence becomes a useful product interaction rather than a standalone demonstration. That connects this story with the day’s broader emphasis on integrating AI into established systems. However, the supplied excerpt does not disclose the architecture, evaluation methods, or member outcomes, so it cannot establish which design choices worked or whether discovery improved.

*Sources: [Netflix Tech Blog](https://netflixtechblog.com/engineering-ai-discover-e244944cdc38?source=rss----2615bd06b42e---4)*

### [SPFx Dev Skills for SPFx 1.24.1: tested across agents and models](https://devblogs.microsoft.com/microsoft365dev/spfx-dev-skills-for-spfx-1-24-1-tested-across-agents-and-models/)
*Microsoft presents measured evidence that framework-specific guidance can improve agent-assisted upgrades.*

SPFx Dev Skills v1.1.2 adds support for SharePoint Framework 1.24.1 and React 18 migration. Microsoft reports that, across 105 evaluation runs, the updated skill improved upgrade quality for every tested agent-and-model combination; six of seven combinations achieved a 100% mean score. The meaningful change is therefore both version support and a reported improvement across multiple execution environments.

For teams assessing coding agents, this points toward evaluating the guidance supplied to a model alongside the model itself. Framework migrations are a concrete setting in which specialized instructions can be measured against an upgrade task. Still, these are publisher-reported results: the excerpt does not provide the scoring rubric, task distribution, or production outcomes. A perfect mean on that evaluation should not be read as a guarantee of flawless migrations.

*Sources: [Microsoft 365 Developer Blog](https://devblogs.microsoft.com/microsoft365dev/spfx-dev-skills-for-spfx-1-24-1-tested-across-agents-and-models/)*

### [How to prevent Electron safeStorage decryption errors from deleting API keys](https://dev.to/orca_forge/how-to-prevent-electron-safestorage-decryption-errors-from-deleting-api-keys-2hka)
*An Electron incident illustrates how destructive error handling can turn an access failure into data loss.*

A screen-check script accessed the same settings location as the production Electron application while using a differently signed executable. Decryption failed, and the error handler deleted all four API keys. The central failure was not simply that ciphertext became unreadable: the application treated that condition as a reason to remove the stored values.

The reported fix preserves unreadable ciphertext under another name and retries decryption when reading it, while keeping the check script away from `getSettings()` and `safeStorage`. These changes address both recovery and the tooling boundary that triggered the incident. The broader lesson is to distinguish “unavailable in this execution context” from “safe to discard.” The excerpt supports that distinction without establishing the underlying platform-specific signing mechanics or guaranteeing that every preserved value will become readable again.

*Sources: [Dev.to](https://dev.to/orca_forge/how-to-prevent-electron-safestorage-decryption-errors-from-deleting-api-keys-2hka)*

### [Vercel Releases UI SDK for Agents to Compose UI from Reusable Behaviors](https://www.infoq.com/news/2026/11/vercel-ui-sdk/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)
*Reusable interaction behaviors offer agents a more structured foundation for building interfaces.*

Vercel has released UI SDK in beta as an Apache 2.0 TypeScript library. InfoQ reports that `@ui-sdk/core` contains more than 50 UI behaviors, with adapters for React, Vue, Svelte, Solid, and Web Components. The SDK is intended to let agents compose accessible components and operate them through a documented agent bridge, connecting interface construction with subsequent interaction.

The architectural appeal is reuse: agents can work from defined behaviors rather than inventing each interaction independently. That also creates a clearer surface for teams to inspect than unconstrained generated UI code. However, the beta release and stated accessibility purpose do not demonstrate that every composed interface will be accessible or reliable. The supplied material includes no comparative evaluation, so those outcomes remain matters for application-level verification.

*Sources: [InfoQ](https://www.infoq.com/news/2026/11/vercel-ui-sdk/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)*

### [Resetting Vue State When Related Converter Routes Reuse One Component](https://dev.to/begoodtool/resetting-vue-state-when-related-converter-routes-reuse-one-component-3hgb)
*Shared route components need explicit state-reset behavior when navigation does not create a new instance.*

This Vue case study examines related converter URLs rendered by one shared component. Moving between those URLs does not necessarily create a fresh component instance, so editable input refs can outlive the page identity they originally represented. The application defines conversion pairs as data and places the pair slug in route metadata, allowing the component to resolve the current definition.

The difficult part is coordinating route-driven defaults with two-way calculations: resetting one input can activate watchers that overwrite the intended value on the other side. The feet-to-meters arithmetic is incidental; the reusable lesson is that route identity, editable state, and synchronization need a deliberate relationship. The supplied excerpt establishes the problem and data model but does not include the complete reset implementation, so it does not support prescribing a particular watcher sequence.

*Sources: [Dev.to](https://dev.to/begoodtool/resetting-vue-state-when-related-converter-routes-reuse-one-component-3hgb)*

## Cloud

### [GPT-6.2 Astra and Sol now available on AI Gateway](https://vercel.com/changelog/gpt-6-2-astra-and-sol-now-available-on-ai-gateway)
*Vercel adds two models with different stated workload targets to its gateway.*

Vercel says OpenAI’s GPT-6.2 Astra and GPT-6.2 Sol are now available through AI Gateway. Astra is positioned for complex, multistep projects, including implementing and testing changes in existing codebases, following document templates, and computer use. Sol is positioned for everyday coding, writing, and agent workflows, including creating interactive web applications from written briefs.

The concrete integration details are the model IDs, `openai/gpt-6.2-astra` and `openai/gpt-6.2-sol`, and the use of an AI Gateway key through `AI_GATEWAY_API_KEY`. Availability gives teams another deployment option, but the workload descriptions remain product claims rather than comparative evidence. The supplied announcement provides no pricing, latency, or independent quality results, so it does not establish which model offers the better operational trade-off for a particular application.

*Sources: [Vercel](https://vercel.com/changelog/gpt-6-2-astra-and-sol-now-available-on-ai-gateway)*

### [Introducing Azure Catalyst agentic modernization and new AI infrastructure innovations](https://azure.microsoft.com/en-us/blog/introducing-azure-catalyst-agentic-modernization-and-new-ai-infrastructure-innovations/)
*Microsoft frames agent infrastructure as a coordinated systems problem rather than an isolated model choice.*

Microsoft’s Ignite announcement presents models, silicon, and cloud infrastructure as a co-engineered system. It identifies isolated execution, networking, context management, and inference efficiency as areas of new capability, claiming improvements to agent speed, security, and unit economics. The emphasis is on tuning the stack together rather than treating infrastructure as a neutral host for interchangeable models.

That framing is relevant to teams whose agent workloads cross execution, data, and networking boundaries. It also leaves important questions unanswered in the supplied material: the excerpt does not describe Azure Catalyst’s modernization workflow, quantify the improvements, or distinguish availability stages for individual capabilities. The announcement therefore establishes Microsoft’s direction, not enough evidence to calculate savings or assume particular security properties for a deployment.

*Sources: [Azure Blog](https://azure.microsoft.com/en-us/blog/introducing-azure-catalyst-agentic-modernization-and-new-ai-infrastructure-innovations/)*

### [AWS PrivateLink Tunnel Endpoints Open a Whole CIDR Range to Another Account](https://www.infoq.com/news/2026/11/aws-privatelink-tunnel-endpoints/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)
*Network-segment access expands PrivateLink’s reach while introducing explicit traffic and observability constraints.*

AWS has detailed PrivateLink tunnel endpoints that let a consumer VPC access an entire network segment in another account instead of connecting one resource at a time. According to InfoQ, the arrangement accommodates overlapping address spaces and permits only consumer-initiated connections. This changes the unit of connectivity from an individual resource to a broader network range.

The wider reach comes with concrete integration limits: consumers must wrap traffic in GENEVE, only TCP and DNS traffic pass, and access logs cannot identify the workload behind an endpoint. Those constraints make protocol compatibility and attribution central design questions, not implementation details to defer. Segment-level access may fit some connectivity requirements better, but the supplied facts do not support treating it as a transparent substitute for every existing PrivateLink configuration.

*Sources: [InfoQ](https://www.infoq.com/news/2026/11/aws-privatelink-tunnel-endpoints/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)*

### [Nvidia clarifies when it will — and won’t —keep financing neoclouds](https://techcrunch.com/2026/11/18/nvidia-clarifies-when-it-will-and-wont-keep-financing-neoclouds/)
*Nvidia’s explanation makes the conditions attached to infrastructure financing more important than the headline commitment.*

Interim Nvidia CEO Colette Kress described conditions governing the company’s exposure when it backstops a data-center loan. TechCrunch reports that Nvidia will not be on the hook unless the neocloud has independent financing, completes the facility, and installs Nvidia equipment. The clarification separates a conditional commitment from an unconditional promise to fund construction.

For readers assessing AI infrastructure expansion, the implication is that announced backing should not automatically be counted as immediately available project financing. The described arrangement depends on other funding and completed infrastructure before Nvidia’s obligation applies. The excerpt does not provide contract terms, amounts, or project-specific details, so it cannot establish the scale of Nvidia’s eventual exposure or whether any particular facility will reach those milestones.

*Sources: [TechCrunch](https://techcrunch.com/2026/11/18/nvidia-clarifies-when-it-will-and-wont-keep-financing-neoclouds/)*

## 🔧 DevOps & SRE

### [Optimizing Kubernetes admission control: Where Kyverno’s CEL admission cost actually goes](https://www.cncf.io/blog/2026/11/18/optimizing-kubernetes-admission-control-where-kyvernos-cel-admission-cost-actually-goes/)
*Profiling challenges the assumption that policy-expression evaluation dominates admission overhead.*

The Kyverno account starts with a plausible expectation: because its CEL-based engines evaluate policy expressions, CEL evaluation should account for most admission-path cost. Profiling did not support that expectation. The useful finding in the supplied excerpt is the mismatch between the component’s apparent purpose and where its measured expense actually lay.

That is a practical warning against selecting optimization targets from architecture diagrams alone. Admission processing needs to be measured as a complete path before effort is concentrated on expression execution. The excerpt ends immediately after “About 86%,” without identifying what that percentage measures or where it belongs. Consequently, it cannot support a numerical breakdown, a specific bottleneck diagnosis, or a recommendation to optimize any named subsystem.

*Sources: [CNCF Blog](https://www.cncf.io/blog/2026/11/18/optimizing-kubernetes-admission-control-where-kyvernos-cel-admission-cost-actually-goes/)*

### [Azure DevOps and GitHub: Start Your Agentic Journey Where You Are](https://devblogs.microsoft.com/devops/azure-devops-and-github-start-your-agentic-journey-where-you-are/)
*Microsoft extends agent-related capabilities to teams retaining their repositories in Azure Repos.*

Microsoft says the GitHub Copilot app now works with Azure Repos and that Copilot Code Review for Azure DevOps is generally available. These are distinct developments: one extends the app’s repository compatibility, while the other establishes a release milestone for code review. Together, they bring more of GitHub’s agent-related tooling to an existing Azure DevOps workflow.

The practical implication is that adopting these capabilities need not begin with moving source code out of Azure Repos. That separates repository-location decisions from at least some tooling-adoption decisions. The excerpt also starts an announcement about Copilot Autofix but cuts off before describing it; no availability or behavior can be inferred for that item. Nor does the supplied material establish permission requirements, supported scenarios, or measured review effectiveness.

*Sources: [Azure DevOps Blog](https://devblogs.microsoft.com/devops/azure-devops-and-github-start-your-agentic-journey-where-you-are/)*

### [Yelp Migrates Cassandra to EKS by Moving EBS Volumes](https://www.infoq.com/news/2026/11/kubernetes-cassandra-eks/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)
*Yelp’s migration changes the Kubernetes environment while retaining existing storage volumes.*

Yelp moved its Cassandra fleet from legacy self-managed Kubernetes clusters to Amazon EKS by re-pointing existing EBS volumes at new pods. Rather than streaming data between Cassandra nodes as the migration mechanism, the reported approach reused the volumes already holding it. The distinguishing choice is therefore how the state crossed the infrastructure transition, not simply the adoption of managed Kubernetes.

This offers a useful migration pattern to investigate when a platform change does not also require replacing the underlying storage. It should not, however, be mistaken for a universally portable procedure. The supplied account gives no outage duration, consistency checks, rollback design, or storage-placement details. Those omissions prevent conclusions about zero downtime, quantified savings, or whether the same sequence would be appropriate for another Cassandra deployment.

*Sources: [InfoQ](https://www.infoq.com/news/2026/11/kubernetes-cassandra-eks/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)*

## Security

### [France Is Blaming Iran for the Fridge Cyberattack](https://www.schneier.com/blog/archives/2026/11/france-is-blaming-iran-for-the-fridge-cyberattack.html)
*The attribution story turns on the limited confidence of the intelligence assessment.*

Schneier on Security highlights reporting that U.S. intelligence agencies reached a low-confidence assessment linking attacks in France to Iran. The quoted account relies on three unnamed U.S. officials and explains that low confidence reflects fragmented intelligence that could lead to a revised judgment. Two officials said the assessment concerned Iran generally, not a particular organization such as the Revolutionary Guards.

The distinction between suspicion and established attribution is essential here. The quoted reporting also describes Iran as probably responsible for similar incidents elsewhere in Europe, while noting that those investigations were at an early stage. Neither that language nor the headline establishes a confirmed operator or technical attack mechanism. The defensible conclusion is that an attribution assessment exists, but its evidentiary limits remain part of the story rather than a footnote.

*Sources: [Schneier on Security](https://www.schneier.com/blog/archives/2026/11/france-is-blaming-iran-for-the-fridge-cyberattack.html), [The New York Times, as quoted](https://www.nytimes.com/2026/11/09/world/europe/france-iran-refrigerators-cyberattack.html)*

### [CISA Urges Immediate Patching of Java4Shell Flaw That Could Allow Remote Code Execution](https://thehackernews.com/2026/11/cisa-urges-immediate-patching-of.html)
*A reported CISA warning makes Java patch exposure an immediate operational concern.*

The Hacker News reports that CISA has urged organizations to patch a newly disclosed Oracle Java vulnerability, CVE-2026-114938. The supplied description identifies an out-of-bounds write with a CVSS score of 8.1 that can cause denial of service or, under certain conditions, remote code execution. The report calls the flaw critical; the numerical score and conditional impact are the more precise details available here.

For engineering and operations teams, the relevant task is to connect the advisory to the Java deployments they actually operate. The excerpt does not identify affected releases, fixed versions, exploitation prerequisites, or evidence of active exploitation. It therefore supports urgency around checking exposure and applying the relevant patch, but not a claim that every Java installation is affected or that remote execution is possible in every configuration.

*Sources: [The Hacker News](https://thehackernews.com/2026/11/cisa-urges-immediate-patching-of.html)*

### [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/)
*A reported malware campaign demonstrates the reach of third-party website dependencies.*

Krebs on Security reports that at least 178 major web destinations unwittingly served malware exploits during the preceding 24 hours through a vulnerability involving Optimizely. The account names sites including the BBC, CNN, Equifax, Ledger, and Zoom, and describes data-stealing malicious software being silently injected. The supplied material does not identify the precise vulnerability or establish how many visitors were compromised.

The architectural concern is the trust granted to externally supplied website content. Experts quoted in the report say the incident was exacerbated by the limited use of strict restrictions on third-party content sources. That connects user-experience tooling with a wider security boundary: functionality introduced outside the main application still affects visitors. The excerpt supports scrutinizing that boundary, but not asserting that any single browser policy would have prevented every part of this campaign.

*Sources: [Krebs on Security](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/)*

## AI/ML

### [Le Groupe Figaro and OpenAI partner to bring Le Figaro journalism to ChatGPT](https://openai.com/index/le-groupe-figaro-and-openai-announce-partnership)
*The partnership brings publisher material into an AI interface through summaries, excerpts, and source links.*

OpenAI and Le Groupe Figaro have announced a partnership to bring Le Figaro journalism to ChatGPT. The supplied announcement describes summaries and excerpts accompanied by links to the original stories. Those are the concrete presentation elements disclosed: readers encounter material within ChatGPT while retaining a route to the publisher’s reporting.

The arrangement illustrates how AI products can become another interface for published journalism rather than only a destination for generated answers. Links preserve a connection to the original work, but their presence alone does not establish how much traffic or revenue the publisher will receive. The excerpt gives no commercial terms, rollout details, content scope, or training provisions. It would therefore be premature to characterize the agreement as a particular licensing or business model beyond the stated partnership.

*Sources: [OpenAI Blog](https://openai.com/index/le-groupe-figaro-and-openai-announce-partnership)*

### [External sandboxes for coding agents](https://simonwillison.net/2026/Nov/17/external-sandboxes-for-coding-agents/)
*Separating an agent from its execution environment makes the code-running boundary explicit.*

Simon Willison describes work with Prime Radiant on an “external sandbox” pattern: the agent remains outside a dedicated sandbox while the code it executes runs inside. The stated motivation is to make experimentation with local models safer when mistakes or prompt injection could otherwise lead to damaging actions on a machine. Three sandbox-server implementations were released to demonstrate the approach.

The important design distinction is that the execution environment, rather than the entire agent, is placed inside the sandbox. That gives teams a concrete boundary to examine when deciding what agent-generated code may access. It is not, by itself, proof that every dangerous action is contained: the supplied excerpt does not describe permissions, communication interfaces, or isolation guarantees. Those details determine what protection a particular implementation actually provides.

*Sources: [Simon Willison](https://simonwillison.net/2026/Nov/17/external-sandboxes-for-coding-agents/), [Prime Radiant, as introduced in the post](https://blog.primeradiant.com/external-sandboxes-for-coding-agents/)*

### [CoreWeave connects custom training loops to model serving](https://thenewstack.io/coreweave-forge-training-loops/)
*The reported connection addresses the gap between pre-deployment evaluation and failures exposed by real use.*

The New Stack reports on CoreWeave connecting custom training loops to model serving. Its supplied introduction emphasizes that production traffic reveals failures and important edge cases that benchmarks or pre-deployment evaluations cannot fully expose. That positions the work around learning from deployed behavior rather than treating a model’s initial evaluation as the end of development.

The implication is a closer relationship between operating a model and deciding what to improve next. Production evidence can identify problems worth targeting, but observing failures is not equivalent to automatically correcting them. The excerpt does not explain the feedback mechanism, data-selection process, training controls, or release validation. It consequently supports the direction of an integrated workflow, not claims about autonomous retraining, guaranteed quality gains, or reduced operating costs.

*Sources: [The New Stack](https://thenewstack.io/coreweave-forge-training-loops/)*

### [Presentation: Behind Booking.com's AI Evolution: The Unpolished Story](https://www.infoq.com/presentations/bookingcom-ml-data-platform-evolution/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)
*Booking.com’s account places agentic AI within two decades of data-platform evolution.*

Jabez Eliezer Manuel’s presentation traces Booking.com’s data management and ML platforms over 20 years. The supplied description covers scaling MySQL topologies, retiring Hadoop in favor of cloud architecture, and building high-throughput model serving and feature stores operating at a reported 400 billion predictions per day. It also addresses personalization, interleaved experimentation, and a new agentic AI foundation.

The sequence matters because the agentic work appears as part of a longer engineering evolution, not a replacement for the underlying data and serving systems. Alongside the CoreWeave story, it reinforces the importance of production infrastructure and experimentation in AI development. However, the prediction count is an operational scale figure, not evidence of model quality or agent capability. The excerpt does not specify the agentic foundation’s architecture, maturity, or measured results.

*Sources: [InfoQ](https://www.infoq.com/presentations/bookingcom-ml-data-platform-evolution/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)*

### [Nvidia isn’t selling any more AI chips to China](https://www.theverge.com/tech/1036445/nvidia-h200-ai-chips-china-stop-selling)
*A reported halt in shipments separates permission to sell from actual market supply.*

The Verge reports that Nvidia has stopped sending its advanced AI chips to China despite receiving White House approval in December of the previous year. Interim CEO Colette Kress announced the decision during Tuesday’s earnings call. The report presents it as a notable change from the company’s position under former CEO Jensen Huang.

For organizations planning AI capacity, the immediate implication is that regulatory permission alone does not establish that hardware will be commercially available. Actual shipment decisions remain a separate constraint. The supplied excerpt does not explain why Nvidia stopped, which products or existing arrangements are affected, or whether shipments might resume. It therefore supports identifying a supply-policy change, but not attributing it to a particular political demand, commercial calculation, or leadership dispute.

*Sources: [The Verge](https://www.theverge.com/tech/1036445/nvidia-h200-ai-chips-china-stop-selling)*

## Quick Reads

---

- **[Full-disk encryption on a VPS: what it really protects](https://dev.to/eqvps/full-disk-encryption-on-a-vps-what-it-really-protects-3bal)** — This article examines what full-disk encryption actually protects on a VPS, looking beyond the checkbox on a hosting plan. *Source: [Dev.to (Top)](https://dev.to/eqvps/full-disk-encryption-on-a-vps-what-it-really-protects-3bal)*

- **[Use open job postings as a sales signal: which companies are hiring for what, from just a domain](https://dev.to/lindenbyte/use-open-job-postings-as-a-sales-signal-which-companies-are-hiring-for-what-from-just-a-domain-p9i)** — This post explores using company domains to find hiring activity as a sales signal. Its author discloses building the Apify Actor featured in the post and using AI assistance to draft it. *Source: [Dev.to (Top)](https://dev.to/lindenbyte/use-open-job-postings-as-a-sales-signal-which-companies-are-hiring-for-what-from-just-a-domain-p9i)*

- **[Why your Laravel deploy still serves the old code (and how to fix OPcache)](https://dev.to/amjadiqbal/why-your-laravel-deploy-still-serves-the-old-code-and-how-to-fix-opcache-52a5)** — This troubleshooting article addresses OPcache when a Laravel site continues behaving like the old release despite updated files on the server. *Source: [Dev.to (Top)](https://dev.to/amjadiqbal/why-your-laravel-deploy-still-serves-the-old-code-and-how-to-fix-opcache-52a5)*

- **[Qwen3 + Claude Code: Request Routing Sent 96% to the Cloud, Step Routing Kept 48% Local](https://dev.to/kenimo49/qwen3-claude-code-request-routing-sent-96-to-the-cloud-step-routing-kept-48-local-3143)** — The author reports that whole-request routing sent 96% of requests to the cloud, while step-level routing kept 48% local. The post compares local Qwen3 routing approaches for Claude Code. *Source: [Dev.to (Top)](https://dev.to/kenimo49/qwen3-claude-code-request-routing-sent-96-to-the-cloud-step-routing-kept-48-local-3143)*

- **[Operators, conditions and loops (VB.NET)](https://dev.to/divakarupadhyay/operators-conditions-and-loops-vbnet-3lc3)** — This VB.NET lesson covers operators, conditions, and loops, with a link to the full lesson on DevLadder. *Source: [Dev.to (Top)](https://dev.to/divakarupadhyay/operators-conditions-and-loops-vbnet-3lc3)*

- **[RxJS parte 4: Subjects, hot vs cold e um mini store](https://dev.to/edwardteixeira/rxjs-parte-4-subjects-hot-vs-cold-e-um-mini-store-7md)** — Part four of this Portuguese-language RxJS series covers Subjects, hot versus cold observables, and a mini store. *Source: [Dev.to (Top)](https://dev.to/edwardteixeira/rxjs-parte-4-subjects-hot-vs-cold-e-um-mini-store-7md)*

- **[Match paths the way Spring MVC does: an encoded-path bypass in API-key auth](https://dev.to/tenmatech/match-paths-the-way-spring-mvc-does-an-encoded-path-bypass-in-api-key-auth-3jj6)** — The author describes an encoded-path bypass in API-key authentication and the importance of matching paths consistently with Spring MVC. The implementation lets tenants authenticate integrations using an `X-API-Key` header instead of a JWT. *Source: [Dev.to (Top)](https://dev.to/tenmatech/match-paths-the-way-spring-mvc-does-an-encoded-path-bypass-in-api-key-auth-3jj6)*

- **[How to generate an architecture diagram from a GitHub repo](https://dev.to/repowise/how-to-generate-an-architecture-diagram-from-a-github-repo-2nof)** — This guide lists GitDiagram, Eraser, and repowise as tools for generating architecture diagrams from a GitHub repository URL. *Source: [Dev.to (Top)](https://dev.to/repowise/how-to-generate-an-architecture-diagram-from-a-github-repo-2nof)*

- **[AskDB: AI-written SQL and charts, without AI seeing your data](https://dev.to/ygilany/askdb-ai-written-sql-and-charts-without-ai-seeing-your-data-2jdm)** — This post presents AskDB as a way to generate SQL and charts with AI without exposing database data to the AI. *Source: [Dev.to (Top)](https://dev.to/ygilany/askdb-ai-written-sql-and-charts-without-ai-seeing-your-data-2jdm)*

- **[How an options desk earns the right to trade real money](https://dev.to/ankushyadavdev/how-an-options-desk-earns-the-right-to-trade-real-money-2nbg)** — The post says Strikedeck requires a strategy to complete 50 paper trades with a win rate of at least 45% before trading real money, alongside daily loss caps. *Source: [Dev.to (Top)](https://dev.to/ankushyadavdev/how-an-options-desk-earns-the-right-to-trade-real-money-2nbg)*

- **[Nvidia says it does not intend to reinstate Jensen Huang as CEO](https://www.theverge.com/report/1035465/nvidia-says-it-will-not-reinstate-jensen-huang-as-ceo)** — The Verge reports that Nvidia does not intend to reinstate Jensen Huang as CEO. New board chair Harvey Jones addressed Huang’s resignation at the start of Tuesday’s quarterly earnings call. *Source: [The Verge - Tech](https://www.theverge.com/report/1035465/nvidia-says-it-will-not-reinstate-jensen-huang-as-ceo)*

- **[China dominates battery graphite, but this startup could break the monopoly](https://techcrunch.com/2026/11/18/china-dominates-battery-graphite-but-this-startup-could-break-the-monopoly/)** — Molten Industries says its new Oakland factory could challenge Chinese companies’ near-total dominance of the graphite industry, TechCrunch reports. *Source: [TechCrunch](https://techcrunch.com/2026/11/18/china-dominates-battery-graphite-but-this-startup-could-break-the-monopoly/)*

- **[India’s Humyn Labs raises $47M to feed U.S. robotics companies the data they need](https://techcrunch.com/2026/11/18/accel-backs-indias-humyn-labs-to-supply-training-data-needed-by-u-s-robotics-ai-developers/)** — TechCrunch reports that Humyn Labs raised $47 million to supply training data to U.S. robotics companies. Founded in February, the startup gets about 90% of its revenue from the U.S. *Source: [TechCrunch](https://techcrunch.com/2026/11/18/accel-backs-indias-humyn-labs-to-supply-training-data-needed-by-u-s-robotics-ai-developers/)*

- **[AI Pentesting Checklist for Web Apps: 15 Questions to Ask Before Choosing a Vendor](https://thehackernews.com/2026/11/ai-pentesting-checklist-for-web-apps-15.html)** — This checklist presents 15 questions for evaluating AI penetration-testing vendors for web applications. *Source: [The Hacker News](https://thehackernews.com/2026/11/ai-pentesting-checklist-for-web-apps-15.html)*

- **[Quality Isn’t The Main Worry About AI Pentesting — Data Privacy and Production Safety Are](https://thehackernews.com/2026/11/quality-isnt-main-worry-about-ai.html)** — This article argues that data privacy and production safety, rather than testing quality alone, are central concerns when adopting AI penetration testing. *Source: [The Hacker News](https://thehackernews.com/2026/11/quality-isnt-main-worry-about-ai.html)*

- **[Java4Shell Flaw (CVE-2026-114938) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html)** — The Hacker News reports that a Java flaw dubbed Java4Shell, tracked as CVE-2026-114938, can allow unauthenticated remote code execution in Jira, Jenkins, Keycloak, and three other applications. *Source: [The Hacker News](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html)*

- **[How Shopify Orchestrates AI-Powered Mobile App Development Without Overloading Developers' Machines](https://www.infoq.com/news/2026/11/shopify-remote-ai-dev/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)** — InfoQ examines Shopify’s approach to orchestrating AI-powered mobile app development without overloading developers’ machines. *Source: [InfoQ](https://www.infoq.com/news/2026/11/shopify-remote-ai-dev/?utm_campaign=infoq_content&utm_source=infoq&utm_medium=feed&utm_term=global)*

- **[Deterministic Simulation Testing](https://martinfowler.com/articles/deterministic-simulation-testing.html)** — This article explores deterministic simulation testing for distributed systems, where partial failures can overlap with live traffic and produce different execution paths. *Source: [Martin Fowler](https://martinfowler.com/articles/deterministic-simulation-testing.html)*

- **[Risky Business #860 -- Google: Agentic hacking has “crossed a threshold”](https://risky.biz/RB860/)** — Patrick Gray and James Wilson are joined by METR.org CISO Jason Kikta to discuss cybersecurity news, including Google’s assessment that agentic hacking has “crossed a threshold.” *Source: [Risky Business (Podcast)](https://risky.biz/RB860/)*

- **[How to automate Telegram with your AI agent and Zapier](https://zapier.com/blog/automate-telegram)** — This guide covers automating Telegram with an AI agent and Zapier, in the context of messaging-based business interactions. *Source: [Zapier Engineering](https://zapier.com/blog/automate-telegram)*

- **[Representative Line: Terning White as a (Style)Sheet](https://thedailywtf.com/articles/terning-white-as-a-style-sheet)** — This installment recounts a story from Stefan’s company, which had a short-handed development team but a large help-desk support team. *Source: [The Daily WTF](https://thedailywtf.com/articles/terning-white-as-a-style-sheet)*

- **[Nvidia’s startup stakes ballooned to $65B, but Huang’s exit puts future  deals in doubt](https://techcrunch.com/2026/11/17/nvidias-startup-stakes-ballooned-to-65b-but-huangs-exit-puts-future-deals-in-doubt/)** — TechCrunch reports that Nvidia’s private investments reached $65 billion, nearly tripling in value over nine months. The report examines uncertainty around future deals following Jensen Huang’s exit. *Source: [TechCrunch](https://techcrunch.com/2026/11/17/nvidias-startup-stakes-ballooned-to-65b-but-huangs-exit-puts-future-deals-in-doubt/)*

- **[Lovable Wants You to Vibe Code Your Dream Job](https://www.wired.com/story/lovable-wants-you-to-vibe-code-a-living/)** — Wired reports that Swedish startup Lovable is shifting from helping users build vibe-coded apps toward helping them run vibe-coded businesses, two years after launch. *Source: [Wired](https://www.wired.com/story/lovable-wants-you-to-vibe-code-a-living/)*

- **[Building the Agent Host Protocol for sessions that continue across devices](https://github.blog/engineering/engineering-principles/building-the-agent-host-protocol-for-sessions-that-continue-across-devices/)** — GitHub describes building the open Agent Host Protocol to keep agent sessions accessible across editors, apps, phones, and the cloud. *Source: [GitHub Engineering](https://github.blog/engineering/engineering-principles/building-the-agent-host-protocol-for-sessions-that-continue-across-devices/)*

- **[Exclusive: Germ DM Is a Signal Alternative That’s Now on Android](https://www.wired.com/story/germ-dm-is-now-available-on-android/)** — Wired reports that encrypted messaging platform Germ DM is now available on Android. It uses “burner cards” rather than phone numbers or usernames to compartmentalize conversations. *Source: [Wired](https://www.wired.com/story/germ-dm-is-now-available-on-android/)*

- **[Quiz: Nuitka: Compile Python Into a Standalone Executable](https://realpython.com/quizzes/nuitka/)** — This quiz tests knowledge of compiling Python with Nuitka, including standalone and onefile builds, speedups, and when PyInstaller may be a better fit. *Source: [Real Python](https://realpython.com/quizzes/nuitka/)*

- **[Blender on Tablet: Path to Release](https://code.blender.org/2026/11/tablet-path-to-release/)** — Blender’s development blog outlines the path toward releasing its tablet project following a week-long workshop at Blender HQ in October 2026. *Source: [Blender Development](https://code.blender.org/2026/11/tablet-path-to-release/)*

- **[Quad9’s withdrawal from France: A canary in the coal mine](https://blog.cloudflare.com/quad9-withdrawal-from-france/)** — Cloudflare argues that Quad9’s forced withdrawal from France illustrates the risks of mandated DNS-level blocking by public resolvers. *Source: [Cloudflare Blog](https://blog.cloudflare.com/quad9-withdrawal-from-france/)*

- **[Introducing the new Microsoft IQ: Putting your organization’s intelligence to work in every agent](https://azure.microsoft.com/en-us/blog/introducing-the-new-microsoft-iq-putting-your-organizations-intelligence-to-work-in-every-agent/)** — Microsoft introduces Microsoft IQ as an enterprise context management platform intended to bring organizational intelligence into agents. *Source: [Azure Blog](https://azure.microsoft.com/en-us/blog/introducing-the-new-microsoft-iq-putting-your-organizations-intelligence-to-work-in-every-agent/)*

- **[Azure Cobalt 200 VMs now available, proven on real workloads and built for the agentic era](https://azure.microsoft.com/en-us/blog/azure-cobalt-200-vms-now-available-proven-on-real-workloads-and-built-for-the-agentic-era/)** — Microsoft announces the availability of Azure Cobalt 200 VMs, claiming improved performance and efficiency for cloud-native applications, databases, developer tools, and agentic AI workloads. *Source: [Azure Blog](https://azure.microsoft.com/en-us/blog/azure-cobalt-200-vms-now-available-proven-on-real-workloads-and-built-for-the-agentic-era/)*