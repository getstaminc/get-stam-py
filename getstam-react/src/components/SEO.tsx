import React from "react";
import { Helmet } from "react-helmet-async";

const BASE_URL = "https://www.getstam.com";
const DEFAULT_OG_IMAGE = `${BASE_URL}/logo192.png`;

interface SEOProps {
  title: string;
  description: string;
  canonicalPath?: string;
  ogImage?: string;
}

const SEO: React.FC<SEOProps> = ({
  title,
  description,
  canonicalPath,
  ogImage = DEFAULT_OG_IMAGE,
}) => {
  const fullTitle = `${title} | GetSTAM`;
  const canonicalUrl = canonicalPath ? `${BASE_URL}${canonicalPath}` : undefined;

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      {canonicalUrl && <link rel="canonical" href={canonicalUrl} />}

      {/* Open Graph */}
      <meta property="og:site_name" content="GetSTAM" />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:type" content="website" />
      {canonicalUrl && <meta property="og:url" content={canonicalUrl} />}
      <meta property="og:image" content={ogImage} />

      {/* Twitter Card */}
      <meta name="twitter:card" content="summary" />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={ogImage} />
    </Helmet>
  );
};

export default SEO;
