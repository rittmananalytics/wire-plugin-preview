import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';
import styles from './index.module.css';

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/intro">
            Get started
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            style={{marginLeft: '1rem'}}
            to="/docs/getting-started/installation">
            Installation
          </Link>
        </div>
      </div>
    </header>
  );
}

const features = [
  {
    title: '313 slash commands',
    description:
      'A complete command set covering every phase of a data platform engagement, from problem definition through to enablement. A command stops if the step it depends on is not finished.',
  },
  {
    title: '12 release types',
    description:
      'Discovery (diagnostic or modelling-led), dbt development, full platform, platform migration, droughty, and more. Each one carries a machine-readable definition of its own workflow.',
  },
  {
    title: 'Works in Claude Code and Gemini CLI',
    description:
      'The same commands run on both runtimes. Install the Wire plugin for Claude Code or the Wire extension for Gemini CLI — specs are shared between them.',
  },
];

const whatsNew = [
  {
    title: 'The process is enforced, not described',
    description:
      'Every release type has a machine-readable definition of its phases and what depends on what. A shared gate reads it and stops a command whose prerequisites are not met. Overriding takes your name and a reason, both recorded.',
    to: '/docs/advanced/registries',
    linkText: 'How the registries work',
  },
  {
    title: 'Agree what the numbers mean first',
    description:
      'An optional first step records, per business domain, every competing definition of a metric, the file it came from, what they disagree on, and who approved the decision. Disputed rules generate a reconciliation query that runs immediately rather than surfacing in testing.',
    to: '/docs/advanced/business-rules',
    linkText: 'Business rules discovery',
  },
  {
    title: 'Start from a model that already exists',
    description:
      'Where a client models their data in Modality, Wire reads the entities, sources and relationships from it instead of deriving them again. The requirements are still read, and the difference between the two is raised as a finding.',
    to: '/docs/advanced/modality-models',
    linkText: 'Reading a Modality model',
  },
  {
    title: 'Discovery that produces a model',
    description:
      'SOP discovery now has two routes. The default diagnoses. The modelling-led route replaces the three analyses with a current-state appraisal and a signed-off conceptual and logical model, and produces the roadmap before the playback.',
    to: '/docs/release-types/discovery-sop',
    linkText: 'Discovery release types',
  },
];

function WhatsNew({title, description, to, linkText}) {
  return (
    <div className={clsx('col col--6')}>
      <div className="padding-horiz--md padding-vert--md">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
        <Link to={to}>{linkText}</Link>
      </div>
    </div>
  );
}

function Feature({title, description}) {
  return (
    <div className={clsx('col col--4')}>
      <div className="padding-horiz--md padding-vert--lg">
        <Heading as="h3">{title}</Heading>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function Home() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout
      title={siteConfig.title}
      description="AI-accelerated delivery for data platform engagements — Wire Framework documentation">
      <HomepageHeader />
      <main>
        <section style={{padding: '3rem 0'}}>
          <div className="container">
            <div className="row">
              {features.map((props, idx) => (
                <Feature key={idx} {...props} />
              ))}
            </div>
          </div>
        </section>

        <section style={{padding: '0 0 4rem'}}>
          <div className="container">
            <Heading as="h2">New in 4.0</Heading>
            <p style={{maxWidth: '48rem'}}>
              The rules for how a delivery engagement runs used to live inside Wire's
              own source, as prose. They are now data the framework reads and enforces.
            </p>
            <div className="row">
              {whatsNew.map((props, idx) => (
                <WhatsNew key={idx} {...props} />
              ))}
            </div>
            <p style={{marginTop: '1.5rem'}}>
              <Link to="/docs/reference/release-notes">Read the full release notes</Link>
            </p>
          </div>
        </section>
      </main>
    </Layout>
  );
}
